# 📖 Business User Guide: Data Quality & Discrepancy Auditing

This guide explains how the Data Quality Auditing system evaluates your datasets, why each check is important for reports (such as Power BI or Excel dashboards), and how to navigate the findings using the system's interactive dashboard tabs.

---

## 🔍 Part 1: How the Data Quality Agents Work

Our system runs **7 specialized quality checking agents**. Each agent is designed to find specific data entry errors, omissions, or capitalization issues that could corrupt dashboard charts or cause calculations to fail.

### 1. Incomplete Records
* **What it is**: Identifies rows that are missing critical information.
* **How it works**: It scans for standard blank cells, empty text, or placeholder characters that people often type when they do not have the info (such as `?`, `-`, or blank spaces). It ignores valid non-applicable indicators (like `N/A` or `None`).
* **Why it matters**: Missing data can distort calculations like averages, sums, and percentages.
* **Example**: A sales report where the "Joining Date" or "Performance Score" column contains `?` or is left completely blank.

### 2. Wrong Data Type
* **What it is**: Flags cells containing values that do not match the standard datatype of that column.
* **How it works**: It scans the column to see what datatype is used in the vast majority of rows (enforcing a strict 70% majority consensus). Any cell that cannot be converted to this dominant datatype is flagged.
* **Why it matters**: When importing data into tools like Power BI or SAP, columns containing mixed text and numbers will fail to load or crash calculations.
* **Example**: An "Age" or "Salary" column where one cell has the text `"twenty-five"` instead of the number `25`.

### 3. Duplicate Records
* **What it is**: Finds exact duplicate rows and fuzzy (near-duplicate) rows.
* **How it works**:
  * **Exact Duplicates**: Rows that contain identical values across all columns.
  * **Near-Duplicates**: Rows that are extremely similar but have minor typos or spelling differences (e.g. `95%` similarity). It groups transitively (if A matches B, and B matches C, all three are grouped).
* **Why it matters**: Exact duplicates double-count totals and skew sales figures. Near-duplicates create split records for the same customer or product.
* **Example**: Two identical invoice rows representing the same transaction, or `"John Smith, Mumbai"` and `"John Smith, Mumba"`.

### 4. Format Inconsistency
* **What it is**: Identifies columns where values are entered in conflicting formats.
* **How it works**: It converts values into generalized pattern layouts (e.g. numbers to `9`, letters to `a`) and flags any rows that deviate from the column's dominant format layout (minimum 50% majority).
* **Why it matters**: Conflicting formats prevent sorting, filtering, and date calculations.
* **Example**: A date column where some rows are written as `15/01/2024` (DD/MM/YYYY) and others are written as `2024-01-15` (YYYY-MM-DD).

### 5. Out-of-Range Values
* **What it is**: Scans for numbers that are logic violations or statistical extremes.
* **How it works**:
  * Cross-references against hard logical limits (such as Month must be between `1` and `12`, or Age must be `0` to `120`).
  * If no hard limits exist, it calculates statistical boundaries: Z-score (for normal distributions) or Boxplot IQR limits (for skewed distributions).
  * Violations are separated into **Clear Out-of-Range** (extreme typos) and **Borderline Out-of-Range** (requires review).
* **Why it matters**: Catches accidental double-keying typos or negative value entry errors.
* **Example**: An age field containing `312` (clear outlier) or a negative value `-5` (borderline).

### 6. Whitespace & Encoding
* **What it is**: Finds hidden formatting issues like leading/trailing spaces or corrupted text (garbled symbols).
* **How it works**: Uses regular expression scans for double spaces, trailing spaces, and character encoding errors.
* **Why it matters**: Invisible leading or trailing spaces will cause VLOOKUPs, merges, or database joins to fail because `" Delhi "` does not match `"Delhi"`.
* **Example**: A city column containing `" Delhi "` (with spaces) or garbled text containing bytes like `Ã©`.

### 7. Inconsistent Casing
* **What it is**: Identifies capitalization variations of the same word or category.
* **How it works**: Groups identical lowercase words and checks if different capitalizations exist. If the dominant casing style has a majority of at least 50% of the occurrences, the other styles are flagged.
* **Why it matters**: Capitalization differences split dashboard chart categories (e.g. separate bars/columns for `"mumbai"`, `"MUMBAI"`, and `"Mumbai"`).
* **Example**: `"mumbai"` vs `"Mumbai"` when `"Mumbai"` is the standard.

---

## 📊 Part 2: Understanding the Dashboard Tabs

The system presents the results in **6 clean interactive tabs**:

### 1. 📊 Dataset Profiler
* **Purpose**: Provides a high-level overview of the uploaded file's structure and schema.
* **What it displays**:
  * Total rows, columns, and file memory size.
  * Preview of the first 10 rows.
  * A **Column Schema** table showing data types, unique value counts, and completeness percentages.
  * **Value Distribution Expanders** for each column showing the top 5 most frequent values.

### 2. 📊 Summary Dashboard
* **Purpose**: Your initial data health snapshot.
* **What it displays**:
  * **Quality Score**: A score out of 100 representing overall data health.
  * **Impacted Rows**: Percentage of rows affected by one or more issues.
  * **Deduction KPIs**: Percentage of rows with Low, Medium, and High critical issues.
  * **Error Summary Table**: A high-level list classifying issues into logical error categories.
  * **Column Drill Down**: Interactive selectbox where choosing an error category displays a list of the exact columns and issue details.

### 3. 🔍 Row Inspector
* **Purpose**: A debugger to search, filter, and export rows containing specific issues.
* **What it displays**:
  * Two-tier selection dropdowns (Category and Column-Issue).
  * **Search Bar**: Lets you run text searches over the affected rows.
  * **CSV Download Button**: Download the filtered list of discrepant rows for local review.
  * **Paginated Table**: View the full matching rows page-by-page.

### 4. 🔤 Inconsistent Casing Inspector
* **Purpose**: Capitalization standardization tool.
* **What it displays**:
  * Dropdown to select columns with casing errors.
  * For each spelling group: displays the standard correct casing standard, followed by a highlighted table showing only the rows that need casing updates.

### 5. 👯 Duplicate & Near-Duplicate Records Inspector
* **Purpose**: Group-comparison deduplication view.
* **What it displays**:
  * **Toggle Switch**: Switch between inspecting **Exact Duplicates** or **Near-Duplicate Record Candidates**.
  * Shows matching duplicate rows grouped together in unified tables for side-by-side comparison.

### 6. ➕ More ▾ (Drop-Down Selection Menu)
* **Purpose**: Dynamic access to findings, visualizations, and documentation.
* **What it displays**:
  * **Quality Audit Findings**: Expansions grouped by column or issue type, showing discrepant tables with inline mini donut charts.
  * **Visualization**: Interactive bar charts summarizing issues by column, type, and criticality.
  * **System Documentation**: Methodology, deduction score weights, and classifications.
