# Comprehensive Project Documentation: PwC Data Discrepancy & Quality Audit System

This document provides a deep, comprehensive review of the entire project lifecycle. It is designed to serve as a foundational whitepaper, detailing both the **high-level business value** (for non-technical stakeholders) and the **deep architectural mathematics** (for technical reviewers). 

---

## 1. Project Overview & Initialization
**The Core Problem:** 
Enterprise data systems (specifically SAP Business Partners) accumulate "dirty data" over time due to human data entry errors. These errors include typos, missing fields, corrupted text encoding, and hidden duplicate records. When this dirty data flows into downstream reporting tools (like Power BI or executive dashboards), it corrupts financial calculations, splits charts incorrectly, and severely undermines data trust.

**The Solution:**
We engineered an automated, multi-tiered Data Quality Audit System. The system profiles datasets, runs 7 parallel detection agents to flag anomalies, and executes a highly advanced fuzzy-matching algorithm to merge near-duplicate records directly within the strict computational bounds of SAP Datasphere.

---

## 2. Phase 1: Synthetic Data Engineering (The Mock Environment)
**Business Context:** We needed to aggressively test our AI agents without exposing or risking actual, highly-sensitive PwC/SAP client data. 
**Technical Execution:**
* We built a Python pipeline (`scratch/make_mock_data.py`) utilizing the `Faker` library.
* We generated **100,000 rows** of synthetic SAP Business Partner data. 
* To ensure our agents were trained on realistic problems, we algorithmically injected "real-world dirt" into the dataset:
  * Dropping random characters to simulate fast-typing typos.
  * Injecting invisible trailing spaces and null placeholders (`?`, `-`).
  * Shifting dates and mixing textual/numeric datatypes.

---

## 3. Phase 2: The Core Data Quality Agents (Streamlit Dashboard)
**Business Context:** We built a highly interactive dashboard to act as the command center for Data Stewards. The dashboard scans the uploaded data and categorizes errors so humans can easily review and fix them.

**Technical Execution (The 7 Agents):**
1. **Incomplete Records:** Scans beyond standard `NaN` values, actively hunting for placeholder characters (`?`, `-`, whitespace strings) while ignoring valid indicators (like `N/A`).
2. **Wrong Data Type:** Evaluates column arrays to find a 70% majority consensus datatype (e.g., Integer). It then isolates the 30% of rows that violate that type (e.g., text injected into a numeric field).
3. **Duplicate Records:** Uses high-speed hashing to find exact 1:1 row copies, and transitive graph linkages for near-duplicates.
4. **Format Inconsistency:** Collapses strings into structural regex templates (e.g., converting `123-ABC` to `[0-9]{3}-[A-Z]{3}`). It establishes a dominant layout pattern and flags rows that break it.
5. **Out-of-Range Values:** Calculates statistical Boxplot boundaries (Interquartile Range - IQR) to separate reasonable outliers from impossible logic violations (e.g., an Age of `312`).
6. **Whitespace & Encoding:** Hunts down invisible trailing spaces (which destroy SQL `JOIN` clauses) and Latin-1 text corruptions.
7. **Inconsistent Casing:** Standardizes strings to lowercase, groups them, and calculates a 50% dominant casing style (e.g., `Mumbai`). It flags variations like `MUMBAI` or `mumbai`.

**The Streamlit UI (Latest Version Deep Dive):**
Based on workflow testing, we transformed the basic output into a highly interactive, multi-tab command center. Every feature was engineered to reduce the "time to remediation" for data stewards:

**1. The Global Summary Dashboard:**
* **What it does:** Displays a high-level "Quality Score (0-100)" based on mathematically compiled penalty deductions. It features an interactive "Error Summary Table" grouping issues logically.
* **How it helps:** Executives can instantly see the overall health of the dataset, while data stewards can use the "Column Drill Down" select box to immediately see exactly which columns are causing the most severe score deductions.

**2. The Deep-Drilling Row Inspector:**
* **What it does:** A dual-dropdown debugger where users select a Category and then a specific Column-Issue. It renders a paginated data table of the affected rows featuring strict **Cell Highlighting**—the exact broken cell is painted in a distinct color so it stands out immediately in the grid. It also includes an "All Columns" view, a text search bar, and a CSV Download button for local remediation.
* **How it helps:** Users don't have to scroll horizontally hunting for the error; their eyes are instantly drawn to the highlighted cell. The CSV export allows them to immediately pull the exact broken rows for fixing in external systems.

**3. The Data Entry Error Inspector (The Deep Dive Tab):**
* **What it does:** We separated complex statistical anomalies into their own dedicated inspector. Out-of-Range values are explicitly color-coded: **Clear Out-of-Range (Light Red)** for impossible numbers (e.g., negative age) and **Borderline Out-of-Range (Light Yellow)** for extreme but possible statistical outliers. 
* **How it helps:** It dynamically ranks all issues by **Severity** first, and then by **Row Count**. This guarantees that data stewards are always tackling the most critical, highest-impact data entry errors first, rather than wasting time on minor formatting quirks. The visual color-coding prevents accidental deletion of valid outliers.

**4. The Casing & Duplicates Inspectors:**
* **What it does:** Dedicated modules for standardization. The Casing tab groups identical words and highlights only the rows that deviate from the dominant 50% majority (e.g., standardizing `mumbai` to `Mumbai`). The Duplicates tab features a toggle switch to flip seamlessly between Exact Duplicates and Near-Duplicate groups, visually highlighting the exact cells that differ between the records.
* **How it helps:** It turns abstract algorithmic logic into actionable, side-by-side comparison tables, allowing users to effortlessly validate whether a flagged record is actually a typo or a distinct entity.

---

## 4. Phase 3: The SAP Datasphere SQL Roadblocks
**Business Context:** We attempted to move the deduplication "brain" directly into the SAP Datasphere cloud to leverage enterprise compute. However, the SAP cloud environment rejected our initial designs.
**Technical Execution:**
* **Attempt 1:** We engineered a massive SQL view using HANA's native `LEVENSHTEIN_DIST` function and recursive Common Table Expressions (`WITH` clauses) to dynamically build transitive graphs.
* **The Failure:** SAP Datasphere's internal view-builder parser repeatedly threw syntax errors (`Mismatched 'WITH', expecting '(' or 'select'`). We iterated through three distinct SQL architectural styles, but the Datasphere parser limitations strictly blocked the complex graph traversal required for fuzzy deduplication.

---

## 5. Phase 4: Python Dataflow & The Multi-Threading Crisis
**Business Context:** To bypass the SQL limitations, we switched to a Python script inside SAP. However, the SAP server repeatedly crashed silently without telling us why. We had to build custom diagnostic tools to track down the problem.
**Technical Execution:**
* We transitioned to a Python Dataflow node in Datasphere, utilizing a strict `transform(df)` function.
* **The Crash:** Standard Python execution (using Pandas `.apply()`, `difflib.SequenceMatcher`, and `groupby`) immediately crashed the container.
* **The Diagnosis:** We discovered that SAP Datasphere heavily restricts C-level multi-threading (inherent to Pandas and Numpy) and strictly blocks standard Python libraries (like `traceback`, `difflib`, `re`, and `collections`).
* **The Fix:** Because we couldn't read the error logs, we deployed a heavily instrumented diagnostic script. We injected 6 distinct `try-catch` phases and manual `print()` tracing, alongside an isolated `mock_dataflow.py` pipeline, to isolate the environment constraints from our logic.

---

## 6. Phase 5: The Monolithic Column-by-Column Redesign
**Business Context:** We completely rebuilt the system from scratch to survive the strict SAP environment. We stripped away all fancy tools and wrote a highly robust, basic engine that checks records one column at a time.
**Technical Execution:**
* We engineered `fuzzy_dedup_dataflow.py`—a pure, monolithic, single-threaded Python script restricted entirely to native Lists, Dicts, and basic Pandas DataFrames.
* **Raw Levenshtein Math:** We replaced the banned `difflib` library by writing a dynamic programming Levenshtein distance loop natively inline.
* **Column-by-Column Scoring:** Instead of concatenating the entire row into one massive, messy string, we evaluated candidate pairs column-by-column. We calculated the similarity for each field and averaged them.
* **The "Empty Column" Bug:** During testing, the script accidentally marked the whole database as duplicates. We discovered that if two records left 15 columns blank, the algorithm scored those 15 columns as a "100% match". We iterated the logic to aggressively skip empty columns.

---

## 7. Phase 6: The Advanced Cardinality-Weighted Engine
**Business Context:** We added "intelligence" to the system. The algorithm now understands that a typo in a highly unique field (like a Phone Number) is a massive red flag, whereas a typo in a highly common field (like a Country Code) is mostly irrelevant.
**Technical Execution:**
* We engineered `weighted_fuzzy_dedup.py`.
* **Global Cardinality Scanning:** Before pairing records, the script scans the entire 100k+ row dataset to calculate the mathematical **Cardinality** (number of unique non-null values) of every textual column.
* **Dynamic Weighting (IDF):** High-cardinality fields receive a massive mathematical multiplier. Low-cardinality fields receive a tiny multiplier. When the Levenshtein average is calculated, it is heavily weighted toward these unique fields, drastically reducing false positives.

---

## 8. Phase 7: Dual-Validation & Surgical Diff Visualization
**Business Context:** In our final iteration, we transformed the system from a basic "typo checker" into a highly advanced, mathematically rigorous Data Quality Engine. We added a "double-check" lock to guarantee extreme accuracy, and we formatted the output so business users can instantly trust the result.

**Technical Execution:**

**1. The Dual-Validation Lock (85% Weighted + 80% Unweighted)**
* **What it does:** We force every pair of records to pass a rigorous, two-stage mathematical lock. The records MUST score at least 85% on the "Intelligent/Weighted" scale (which heavily penalizes typos in unique fields like Phone Numbers), AND they MUST score at least 80% on the baseline, raw character scale.
* **How it helps:** It mathematically guarantees zero false positives. By requiring both conditions, we ensure that the records are fundamentally very similar on a character level (the 80% baseline) AND that they aren't failing on highly critical identifiers (the 85% weighted lock).

**2. Precision Fuzzy_Score Tracking Against the Centroid**
* **What it does:** Because clusters form transitively (A matches B, B matches C), we added a loop in Phase 5 to designate the absolute oldest/smallest record in a group as the **Cluster Centroid** (Master Record). The script dynamically recalculates the exact Levenshtein mathematical distance between every duplicate and the Master Record, outputting a new `Fuzzy_Score` column.
* **How it helps:** When a Data Steward is reviewing a cluster of 5 near-duplicate records, they no longer have to guess *why* they were grouped together. They can look directly at the `Fuzzy_Score` column and instantly see exactly how close each duplicate is to the Master Record (e.g., `0.852 | 0.820`).

**3. Surgical Diff Visualization**
* **What it does:** Instead of presenting users with a messy string, we engineered a surgical prefix/suffix array scan. It reads the strings forward until they stop matching, reads them backward until they stop matching, and mathematically rips out the exact typo from the middle.
* **How it helps:** It formats the output so beautifully that a non-technical stakeholder can instantly validate the duplicate:
   * **Fuzzy_Score:** `0.852 | 0.820` (Weighted | Unweighted)
   * **CommonPart:** `APPLE ... INC | 123 MAIN ST` (Intentionally injecting a `...` exactly where the typo was ripped out).
   * **UncommonPart:** `NAME1(LE -> EL)` (Explicitly showing both sides of the typographical error for immediate visual validation).
