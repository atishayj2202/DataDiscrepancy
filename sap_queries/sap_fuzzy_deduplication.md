# SAP Datasphere: Whole-Record Fuzzy Deduplication View

Because SAP Datasphere's SQL View builder often throws a `Mismatched "WITH", expecting '(' or 'select'` error (due to a restrictive parser that expects the code to begin with `SELECT`), below are **three different query options**. 

Choose the query that best fits your Datasphere development process. All three accomplish the same fuzzy deduplication logic, but use different structural workarounds to satisfy the compiler.

---

## OPTION 1: Table Function Approach (Highly Recommended)
**Best for**: Complex Graph/Recursive clustering.
**How to use**: Do **not** use the "New SQL View" button. Instead, create a **"New Table Function"** (or SQL Script). The Table Function compiler in Datasphere is much more powerful and natively accepts top-level `WITH` statements without throwing parser errors.

```sql
WITH 
SourceData AS (
    SELECT 
        RecordID AS ID, 
        UPPER(TRIM(COALESCE(Col1, '') || '|' || COALESCE(Col2, '') || '|' || COALESCE(Col3, ''))) AS WholeRecordText,
        SUBSTRING(UPPER(TRIM(COALESCE(Col1, ''))), 1, 4) AS BlockingKey
    FROM YourSchema.YourTableName
),
CandidatePairs AS (
    SELECT 
        a.ID AS ID1, 
        b.ID AS ID2, 
        a.WholeRecordText AS Text1, 
        b.WholeRecordText AS Text2,
        LEVENSHTEIN_DIST(a.WholeRecordText, b.WholeRecordText) AS EditDistance
    FROM SourceData a
    JOIN SourceData b 
      ON a.BlockingKey = b.BlockingKey 
      AND a.ID < b.ID
      AND ABS(LENGTH(a.WholeRecordText) - LENGTH(b.WholeRecordText)) <= 5 
),
ValidPairs AS (
    SELECT ID1, ID2
    FROM CandidatePairs
    WHERE EditDistance <= 0.10 * GREATEST(LENGTH(Text1), LENGTH(Text2))
),
BidirectionalEdges AS (
    SELECT ID1 AS Node, ID2 AS AdjacentNode FROM ValidPairs
    UNION ALL
    SELECT ID2 AS Node, ID1 AS AdjacentNode FROM ValidPairs
    UNION ALL 
    SELECT ID AS Node, ID AS AdjacentNode FROM SourceData
),
ComponentPaths AS (
    SELECT Node, AdjacentNode AS RootNode, 1 AS Depth
    FROM BidirectionalEdges
    UNION ALL
    SELECT c.Node, e.AdjacentNode AS RootNode, c.Depth + 1
    FROM ComponentPaths c
    JOIN BidirectionalEdges e ON c.RootNode = e.Node
    WHERE e.AdjacentNode < c.RootNode AND c.Depth < 5 
),
ClusterRoots AS (
    SELECT Node AS Original_ID, MIN(RootNode) AS Cluster_ID
    FROM ComponentPaths
    GROUP BY Node
)
SELECT 
    c.Cluster_ID,
    s.ID AS RecordID,
    s.WholeRecordText,
    COUNT(*) OVER (PARTITION BY c.Cluster_ID) AS Cluster_Size,
    CASE WHEN COUNT(*) OVER (PARTITION BY c.Cluster_ID) > 1 THEN 'Near Duplicate' ELSE 'Unique' END AS Record_Status
FROM SourceData s
JOIN ClusterRoots c ON s.ID = c.Original_ID
ORDER BY Cluster_Size DESC, c.Cluster_ID, s.ID;
```

---

## OPTION 2: The Nested Subquery Wrapper (For SQL Views)
**Best for**: Standard SQL Views.
**How to use**: If you are restricted to using the "New SQL View" builder, this query wraps the entire CTE logic inside a massive `SELECT * FROM ( ... )` dummy block. This tricks the Datasphere parser into seeing `SELECT` as the very first word, allowing it to bypass the syntax check.

```sql
SELECT * FROM (

    WITH 
    SourceData AS (
        SELECT 
            RecordID AS ID, 
            UPPER(TRIM(COALESCE(Col1, '') || '|' || COALESCE(Col2, '') || '|' || COALESCE(Col3, ''))) AS WholeRecordText,
            SUBSTRING(UPPER(TRIM(COALESCE(Col1, ''))), 1, 4) AS BlockingKey
        FROM YourSchema.YourTableName
    ),
    CandidatePairs AS (
        SELECT 
            a.ID AS ID1, 
            b.ID AS ID2, 
            a.WholeRecordText AS Text1, 
            b.WholeRecordText AS Text2,
            LEVENSHTEIN_DIST(a.WholeRecordText, b.WholeRecordText) AS EditDistance
        FROM SourceData a
        JOIN SourceData b 
          ON a.BlockingKey = b.BlockingKey 
          AND a.ID < b.ID
          AND ABS(LENGTH(a.WholeRecordText) - LENGTH(b.WholeRecordText)) <= 5 
    ),
    ValidPairs AS (
        SELECT ID1, ID2
        FROM CandidatePairs
        WHERE EditDistance <= 0.10 * GREATEST(LENGTH(Text1), LENGTH(Text2))
    ),
    BidirectionalEdges AS (
        SELECT ID1 AS Node, ID2 AS AdjacentNode FROM ValidPairs
        UNION ALL
        SELECT ID2 AS Node, ID1 AS AdjacentNode FROM ValidPairs
        UNION ALL 
        SELECT ID AS Node, ID AS AdjacentNode FROM SourceData
    ),
    ComponentPaths AS (
        SELECT Node, AdjacentNode AS RootNode, 1 AS Depth
        FROM BidirectionalEdges
        UNION ALL
        SELECT c.Node, e.AdjacentNode AS RootNode, c.Depth + 1
        FROM ComponentPaths c
        JOIN BidirectionalEdges e ON c.RootNode = e.Node
        WHERE e.AdjacentNode < c.RootNode AND c.Depth < 5 
    ),
    ClusterRoots AS (
        SELECT Node AS Original_ID, MIN(RootNode) AS Cluster_ID
        FROM ComponentPaths
        GROUP BY Node
    )
    SELECT 
        c.Cluster_ID,
        s.ID AS RecordID,
        s.WholeRecordText,
        COUNT(*) OVER (PARTITION BY c.Cluster_ID) AS Cluster_Size,
        CASE WHEN COUNT(*) OVER (PARTITION BY c.Cluster_ID) > 1 THEN 'Near Duplicate' ELSE 'Unique' END AS Record_Status
    FROM SourceData s
    JOIN ClusterRoots c ON s.ID = c.Original_ID

) AS FuzzyDuplicateClusters
ORDER BY Cluster_Size DESC, Cluster_ID, RecordID;
```

---

## OPTION 3: Zero-WITH-Clause Mode (Nuclear Compatibility)
**Best for**: Strict legacy parsers that aggressively ban the `WITH` keyword entirely.
**How to use**: This version removes the CTEs entirely and rewrites the logic using nested subqueries (derived tables). Because CTEs cannot be used, the base `SourceData` query has to be repeated a few times, but it completely avoids the `WITH` keyword while achieving the same flattened deduplication grouping logic.

```sql
SELECT 
    COALESCE(c.Cluster_ID, s.ID) AS Cluster_ID,
    s.ID AS RecordID,
    s.WholeRecordText,
    COUNT(*) OVER (PARTITION BY COALESCE(c.Cluster_ID, s.ID)) AS Cluster_Size,
    CASE WHEN COUNT(*) OVER (PARTITION BY COALESCE(c.Cluster_ID, s.ID)) > 1 THEN 'Near Duplicate' ELSE 'Unique' END AS Record_Status
FROM (
    -- 1. Source Data (s)
    SELECT 
        RecordID AS ID, 
        UPPER(TRIM(COALESCE(Col1, '') || '|' || COALESCE(Col2, '') || '|' || COALESCE(Col3, ''))) AS WholeRecordText,
        SUBSTRING(UPPER(TRIM(COALESCE(Col1, ''))), 1, 4) AS BlockingKey
    FROM YourSchema.YourTableName
) s
LEFT JOIN (
    -- 4. Simplified Clusters (Grouping Valid Pairs)
    SELECT 
        ID2 AS Original_ID, 
        MIN(ID1) AS Cluster_ID
    FROM (
        -- 3. Valid Pairs (Applying Levenshtein Threshold)
        SELECT ID1, ID2
        FROM (
            -- 2. Candidate Pairs (Applying Blocking Key and Levenshtein)
            SELECT 
                a.ID AS ID1, 
                b.ID AS ID2,
                a.WholeRecordText AS Text1,
                b.WholeRecordText AS Text2,
                LEVENSHTEIN_DIST(a.WholeRecordText, b.WholeRecordText) AS EditDistance
            FROM (
                SELECT 
                    RecordID AS ID, 
                    UPPER(TRIM(COALESCE(Col1, '') || '|' || COALESCE(Col2, '') || '|' || COALESCE(Col3, ''))) AS WholeRecordText,
                    SUBSTRING(UPPER(TRIM(COALESCE(Col1, ''))), 1, 4) AS BlockingKey
                FROM YourSchema.YourTableName
            ) a
            JOIN (
                SELECT 
                    RecordID AS ID, 
                    UPPER(TRIM(COALESCE(Col1, '') || '|' || COALESCE(Col2, '') || '|' || COALESCE(Col3, ''))) AS WholeRecordText,
                    SUBSTRING(UPPER(TRIM(COALESCE(Col1, ''))), 1, 4) AS BlockingKey
                FROM YourSchema.YourTableName
            ) b 
            ON a.BlockingKey = b.BlockingKey 
            AND a.ID < b.ID
            AND ABS(LENGTH(a.WholeRecordText) - LENGTH(b.WholeRecordText)) <= 5 
        ) CandidatePairs
        WHERE EditDistance <= 0.10 * GREATEST(LENGTH(Text1), LENGTH(Text2))
    ) ValidPairs
    GROUP BY ID2
) c ON s.ID = c.Original_ID
ORDER BY Cluster_Size DESC, Cluster_ID, RecordID;
```
