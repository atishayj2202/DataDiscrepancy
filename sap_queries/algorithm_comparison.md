# Fuzzy Deduplication Algorithms Comparison

This document details the mathematical differences between the two pure-Python deduplication Dataflow scripts located in this folder: `fuzzy_dedup_dataflow.py` and `weighted_fuzzy_dedup.py`.

Both scripts are designed to strictly bypass Pandas C-level multi-threading limits in SAP Datasphere by falling back to monolithic, single-threaded Python algorithms, while perfectly extracting and tagging field-level typos (e.g. `NAME1(EL) | STRAS(ST)`).

---

## 1. The Basic Algorithm (`fuzzy_dedup_dataflow.py`)
This script focuses on simplicity and pure execution speed.

### How it Works
1. **Column-by-Column Analysis:** The script pairs records that share the same `LAND1` (Blocking Key). It iterates through every text column and independently calculates the Levenshtein edit distance for each field.
2. **Standard Averaging:** It converts the edit distance to a similarity percentage (0.0 to 1.0) based on the string length. It then averages the percentages across all columns.
   - Example: If `NAME1` has a 90% match, and `CITY` has a 60% match, the final score is exactly `75%`.
3. **Thresholding:** If the overall average score is `> 75%`, it adds the pair to a mathematical graph and extracts the exact typo using a fast prefix/suffix scanner.

**Pros:** Extremely fast, highly predictable, and simple to debug.
**Cons:** It treats all columns equally. A typo in a low-value column (like `CITY`) hurts the score just as much as a typo in a high-value column (like `PHONE`).

---

## 2. The Advanced Algorithm (`weighted_fuzzy_dedup.py`)
This script uses **Dataset Cardinality Weighting** to mathematically penalize discrepancies in fields that are highly unique. 

### How it Works
1. **Global Cardinality Scanning:** Before pairing any records, the script scans the entire dataset to calculate the mathematical cardinality (number of unique non-null values) of every text column.
2. **Dynamic Weight Assignment:** 
   - Fields with **High Cardinality** (e.g. `PHONE_NUMBER`, `STREET_ADDRESS`) get a heavy multiplier. Because values in these fields are rare, if two records match on a rare value, it is a very strong indicator they are duplicates.
   - Fields with **Low Cardinality** (e.g. `CITY`, `STATUS`) get a low multiplier. Many people share the same city, so matching on city doesn't prove much.
3. **Weighted Scoring:** The script calculates the Levenshtein distance for each column, applies the dynamic weight multiplier, and sums them up.
   - Example: A 100% match on a rare `PHONE_NUMBER` might offset a 50% match on a common `CITY`.
4. **Length-of-Change Impact:** The Levenshtein distance is dynamically penalized based on string length (`dist / max_len`). A 3-character typo in a 6-character field (`60%` penalty) will destroy the score much faster than a 3-character typo in a 30-character field (`10%` penalty).

**Pros:** Highly intelligent. It mathematically learns which columns are most important for deduplication based on your actual data distribution.
**Cons:** Slightly slower execution time due to the initial dataset-wide cardinality scan.
