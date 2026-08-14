# Data Quality & Discrepancy Detection System

A generalised, rule-based, and statistical Data Quality & Discrepancy Detection System designed to scan uploaded datasets (CSV or Excel) and rank discrepancies without modifying data.

---

## 🚀 Startup (For Non-Technical Users)

This system is designed to be set up and run easily without typing any command-line code. If you do not have Poetry installed, the launcher script will automatically install it, sync all requirements, and open the application in your browser.

### Option A: Running via Python IDLE App (Simplest - No Command Line Needed)

1. **Download the Project**: Click the green **Code** button at the top of this repository, select **Download ZIP**, and extract it on your computer.
2. **Open the Python Application**: 
   * **On Windows (Start Menu)**: Press the Windows Key on your keyboard, type **IDLE** (Python's built-in application), and click to open it.
   * **On macOS (Spotlight Search)**: Press **Command + Spacebar** to open Spotlight, type **IDLE** (or **Python Launcher**), and press **Enter**.
3. **Open the Launcher Script**: In the IDLE window, click **File** -> **Open...** in the top menu bar, browse to the project folder, and open the `__init__.py` file.
4. **Run the Script**: Once the `__init__.py` code editor window appears, click **Run** -> **Run Module** in the top menu (or simply press **F5** on Windows, or **fn + F5** on Mac).

*That's it! The Python application will configure the virtual environment, install Poetry and package dependencies in the background, and open the web dashboard in your browser automatically.*

---

### Option B: Running via Command Line (Alternative)

1. **Open Terminal / Command Prompt**: 
   * **On Windows**: Press the Windows Key, type **cmd** (Command Prompt), and press Enter.
   * **On macOS**: Press **Command + Spacebar**, type **Terminal**, and press Enter.
2. **Navigate to the Project Folder**: Type `cd ` (with a space), drag the project folder from your file manager directly into the Terminal window, and press Enter.
3. **Run the Command**:
   * **For macOS / Linux**:
     ```bash
     python3 __init__.py
     ```
   * **For Windows**:
     ```bash
     python __init__.py
     ```



---

## ⚙️ Working

This system runs purely locally using deterministic rules and statistical metrics (Z-score, Interquartile Range, and Isolation Forest) without calling any AI APIs (to optimize budget). 

### Requirements
- **Python**: `>=3.9, !=3.9.7` (Note: Python 3.9.7 is excluded due to a known bug in its parser that breaks Streamlit).
- **Poetry**: Used to manage virtual environments and install dependency packages automatically.
- **Dependencies**: `pandas`, `numpy`, `streamlit`, `openpyxl` (Excel support), `scikit-learn` (multivariate outliers), and `rapidfuzz` (near-duplicate matching).

### Project Directory Structure & Component Explanations

* **`__init__.py`**: Root entry point script. It handles platform-independent paths, sets the working directory, executes environment checks, runs `poetry install` in a subprocess, and runs the Streamlit launcher command.
* **`pyproject.toml`**: The Poetry configuration file. Sets project metadata, package versions, python version constraint (`>=3.9, !=3.9.7`), and disables Poetry package distribution mode (`package-mode = false`).
* **`src/`**: Parent directory containing all source code components.
  * **`src/app.py`**: Streamlit dashboard. Injects custom glassmorphic CSS, handles file upload, displays summary stats/column distributions, runs audits showing a live progress log, and renders ranked quality reports.
  * **`src/profiler.py`**: Profiling engine. Scans the file to compute rows, columns, memory usage, cardinality, and top-5 value distributions.
  * **`src/agents/`**: Core discrepancy detection package.
    * **`__init__.py`**: Exposes the agents and issue structures.
    * **`base.py`**: Defines abstract class `BaseAgent` and dataclass `Discrepancy`.
    * **`missing_value.py`**: Finds blanks, NaNs, and placeholder strings (like `"N/A"`, `"-"`, `"null"`). Criticality is assigned as Low (<=5%), Medium (5-30%), or High (>30% of column values).
    * **`wrong_type.py`**: Infers intended column types (Integer, Decimal, Datetime, Boolean) by majority vote. Flags rows containing values that cannot be cast (like `"twenty-five"` in an integer column).
    * **`duplicate.py`**: Identifies exact duplicates and matches near-duplicate record candidates (like spelling variations) using `rapidfuzz` on sorted signatures. Flagged as "For Review" since choosing the authoritative record requires human/AI context.
    * **`format_inconsistency.py`**: Converts strings to format templates (e.g. date characters to `99/99/9999`) and flags rows that depart from the dominant format (>70% frequency).
    * **`out_of_range.py`**: Validates numbers against statistical bounds or custom bounds. Flags borderline cases for manual review.
    * **`whitespace.py`**: Detects leading/trailing spaces, multiple spaces, and encoding mojibake (like UTF-8 decoded as Latin-1).
    * **`inconsistent_casing.py`**: Flags capitalization collisions (e.g. `mumbai` vs `MUMBAI` when `Mumbai` is the dominant form).
    * **`statistical_outliers.py`**: Identifies column-level outliers (IQR/Z-score) and multi-column anomalies by fitting a scikit-learn `IsolationForest` model.

### 📊 Discrepancy Ranking Logic
When findings are collected, the engine ranks discrepancies automatically using a two-tier priority sorting:
1. **Criticality**: sorted by level: `High` > `Medium` > `Low`.
2. **Rows Affected**: sorted by the number of affected rows (highest volume first).
This puts the most severe, high-volume issues at the top of the dashboard.

## ☁️ SAP Datasphere Integration: Advanced Fuzzy Deduplication (`final_sap_dedup.py`)

Beyond the local Data Quality Dashboard, this project includes a massive, production-grade script engineered specifically to run inside an **SAP Datasphere Python Dataflow Node**. Due to extreme environment constraints inside SAP (no multi-threading, strict memory limits, and blocked C-level libraries like `difflib`), we engineered a monolithic, pure-Python deduplication engine from scratch, located at `sap_queries/final_sap_dedup.py`.

Here is a deep-dive breakdown of the 6-Phase architecture executing inside the SAP container:

### Phase 1 & 2: Cardinality-Weighted Blocking
To bypass Pandas' heavy C-level operations, the script immediately converts the dataset into a pure Python list of dictionaries. 
* **Global Cardinality Scanning:** The engine mathematically scans the entire dataset to determine the "uniqueness" of every text column. High-cardinality fields (like Phone Numbers) receive a massive mathematical weight modifier. Low-cardinality fields (like Country Codes) are suppressed. 
* **Blocking:** It groups records by `LAND1` (Country) to drastically reduce the $O(n^2)$ comparison matrix, preventing SAP memory limits from being breached.

### Phase 3: The Dual-Validation Fuzzy Engine & Null-Forgiveness
Instead of concatenating rows into messy strings, it compares records column-by-column using a custom, inline Dynamic Programming Levenshtein Loop.
* **Intelligent Null-Forgiveness:** Missing data is handled probabilistically. If one record has a value but the other is completely blank, it scores that specific field comparison as `0.0` (heavily penalizing the match due to contradiction). If BOTH records are missing data in the exact same field, it scores the field at `0.5` (acknowledging they share the same missing-data state without artificially inflating the score to `1.0`).
* **The Dual-Lock Check:** For a duplicate to be clustered, it must pass a rigorous dual-validation check: It must score **>= 85%** on the Cardinality-Weighted scale, AND **>= 80%** on the pure, unweighted baseline character scale.

### Phase 4: Graph DFS & Centroid Election
Because duplicates form transitive chains (Record A matches Record B; Record B matches Record C), the script uses inline Depth-First Search (DFS) graph traversal to group transitive clusters. It automatically designates the oldest/smallest alphanumeric ID (`KUNNR`) in the cluster as the absolute **Cluster Centroid** (The Master Record).

### Phase 5: Surgical Diff Extraction
To allow non-technical Data Stewards to instantly validate clusters without hunting for typos, the script runs a surgical prefix/suffix array scan:
* **Inline Recalculation:** It mathematically re-calculates the exact Levenshtein distance between every single duplicate and the Master Record, outputting a precise `Fuzzy_Score` column (e.g., `0.852 | 0.820`).
* **CommonPart / UncommonPart:** It literally reads the strings forward and backward to rip out the exact typo, intentionally injecting ellipses (`...`) where the typo occurred (`APPLE ... INC`), and explicitly displaying the typographical error in the uncommon column (`NAME1(LE -> EL)`).
* **Null Diagnostics:** It generates deep null-tracking columns, outputting a global `null_cnt` integer and a boolean `TRUE/FALSE` flag for every specific text column to identify where data drops are occurring.

### Phase 6: Strict Schema Enforcement
SAP Datasphere instantly crashes if a Python node returns a variable output schema. Because our output relies on dynamically generated `[fieldname]_null_flag` columns, the script mathematically guarantees the structural output schema is identical every single time.
* If 0 duplicates are found in the entire database, instead of throwing an error or returning a blank 4-column structure, it injects a single dummy `NO_DATA` row that perfectly maps to the 15+ column target schema, keeping the SAP pipeline permanently stable.
