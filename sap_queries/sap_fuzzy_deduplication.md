# SAP Datasphere: Whole-Record Fuzzy Deduplication View

This SQL query identifies near-duplicate records across the *entire row* (by combining multiple columns into a single string) and groups them using pure SQL Common Table Expressions (CTEs).

### What is `LEVENSHTEIN_DIST`?
**Levenshtein Distance** (also known as Edit Distance) is a mathematical algorithm that counts the minimum number of single-character edits (insertions, deletions, or substitutions) required to change one string into another.
* **Example 1**: "APPLE" vs "APPLES" = **Distance 1** (1 insertion: 'S')
* **Example 2**: "SMITH" vs "SMYTH" = **Distance 1** (1 substitution: 'I' -> 'Y')
* **Example 3**: "DATA" vs "DATA" = **Distance 0** (Exact Match)

By calculating this distance natively in SQL, we can identify records that are mathematically very similar (typos, extra spaces, minor spelling mistakes) without requiring an exact exact `A = B` match.

---

### Instructions:
1. Replace `YourSchema.YourTableName` with your actual schema and table name.
2. Replace `RecordID` with the unique identifier column of your table.
3. Replace `Col1`, `Col2`, `Col3` with the actual columns you want to compare. You can add as many columns as you need to the concatenation.

```sql
WITH 
-- 1. Source Data Preparation (Whole Record Concatenation)
-- We concatenate all relevant columns into a single 'WholeRecordText' string separated by pipes (|).
-- We also extract a 'BlockingKey' (e.g., the first 4 characters).
-- This partitions the database into thousands of smaller "blocks".
SourceData AS (
    SELECT 
        RecordID AS ID, 
        UPPER(TRIM(
            COALESCE(Col1, '') || '|' || 
            COALESCE(Col2, '') || '|' || 
            COALESCE(Col3, '')
        )) AS WholeRecordText,
        
        -- Blocking Key: Limits comparisons to records that start with the same 4 characters.
        -- In a 10-million row database, this prevents a catastrophic 100-Trillion row cross-join,
        -- while guaranteeing all duplicates within a specific entity block are safely compared.
        SUBSTRING(UPPER(TRIM(COALESCE(Col1, ''))), 1, 4) AS BlockingKey
    FROM YourSchema.YourTableName
),

-- 2. Generate Candidate Pairs (Intra-Block Self-Join)
-- We strictly join records that fall into the exact same BlockingKey bucket.
-- `a.ID < b.ID` guarantees we only compare A to B once, never B to A or A to A.
CandidatePairs AS (
    SELECT 
        a.ID AS ID1, 
        b.ID AS ID2, 
        a.WholeRecordText AS Text1, 
        b.WholeRecordText AS Text2,
        -- Calculate Levenshtein Edit Distance on the entire concatenated record natively in HANA
        LEVENSHTEIN_DIST(a.WholeRecordText, b.WholeRecordText) AS EditDistance
    FROM SourceData a
    JOIN SourceData b 
      ON a.BlockingKey = b.BlockingKey 
      AND a.ID < b.ID
      -- Quick length filter to discard massively different strings before running Levenshtein
      AND ABS(LENGTH(a.WholeRecordText) - LENGTH(b.WholeRecordText)) <= 5 
),

-- 3. Filter Valid Pairs based on Dynamic Proportional Threshold
-- Instead of a hardcoded edit distance (e.g., <= 4), we allow the distance to scale based on the record length.
-- Here, we allow up to a 10% error rate (0.10). 
-- This means a 100-character string allows 10 typos, but a 20-character string allows only 2.
ValidPairs AS (
    SELECT ID1, ID2
    FROM CandidatePairs
    -- GREATEST ensures we use the length of the longer string for a fair percentage calculation
    WHERE EditDistance <= 0.10 * GREATEST(LENGTH(Text1), LENGTH(Text2))
),

-- 4. Graph Preparation (Bidirectional Edges)
-- To group records transitively (if A matches B, and B matches C, then A, B, and C are a group).
BidirectionalEdges AS (
    SELECT ID1 AS Node, ID2 AS AdjacentNode FROM ValidPairs
    UNION ALL
    SELECT ID2 AS Node, ID1 AS AdjacentNode FROM ValidPairs
    UNION ALL 
    -- Self-loop to ensure records with no duplicates still get their own unique cluster
    SELECT ID AS Node, ID AS AdjacentNode FROM SourceData
),

-- 5. Recursive CTE: Find Connected Components
-- We traverse the connections to find the absolute minimum Record ID for each group.
-- The minimum Record ID becomes the designated "Cluster ID" for the entire group.
ComponentPaths AS (
    SELECT 
        Node, 
        AdjacentNode AS RootNode, 
        1 AS Depth
    FROM BidirectionalEdges
    
    UNION ALL
    
    SELECT 
        c.Node, 
        e.AdjacentNode AS RootNode, 
        c.Depth + 1
    FROM ComponentPaths c
    JOIN BidirectionalEdges e 
      ON c.RootNode = e.Node
    -- Traverse only towards smaller IDs to quickly find the minimum
    WHERE e.AdjacentNode < c.RootNode 
      -- Stop condition to prevent runaway recursion in massive dense clusters
      AND c.Depth < 5 
),

-- 6. Resolve Cluster Roots
-- Extract the absolute minimum RootNode for each original record.
ClusterRoots AS (
    SELECT 
        Node AS Original_ID, 
        MIN(RootNode) AS Cluster_ID
    FROM ComponentPaths
    GROUP BY Node
)

-- 7. Final Output Assembly
-- Join the computed Cluster IDs back to the original dataset.
SELECT 
    c.Cluster_ID,
    s.ID AS RecordID,
    s.WholeRecordText,
    COUNT(*) OVER (PARTITION BY c.Cluster_ID) AS Cluster_Size,
    CASE 
        WHEN COUNT(*) OVER (PARTITION BY c.Cluster_ID) > 1 THEN 'Near Duplicate' 
        ELSE 'Unique' 
    END AS Record_Status
FROM SourceData s
JOIN ClusterRoots c 
  ON s.ID = c.Original_ID
ORDER BY 
    Cluster_Size DESC, 
    c.Cluster_ID, 
    s.ID;
```
