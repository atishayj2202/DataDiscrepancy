# Data Quality & Discrepancy Detection System

A generalised, rule-based, and statistical Data Quality & Discrepancy Detection System designed to scan uploaded datasets (CSV or Excel) and rank discrepancies without modifying data.

---

## 🚀 Startup (For Non-Technical Users)

This system is designed to be set up and run easily with a **single command**. If you do not have Poetry installed, the launcher script will automatically install it using Python's package installer (`pip`), install all other package requirements, and open the application in your browser.

### Step 1: Download the Project
1. Click the green **Code** button at the top of this repository.
2. Select **Download ZIP** and extract the folder to a location on your computer (e.g., your Desktop).

### Step 2: Open Terminal / Command Prompt (Via Search)
* **On Windows (Start Menu)**: Press the **Windows Key** on your keyboard, type **Command Prompt** (or search for **cmd** or **Python** to open your command line environment), and press **Enter**.
* **On macOS (Spotlight Search)**: Press **Command + Spacebar** to open Spotlight Search, type **Terminal** (or search for **Python** to find the Terminal/launcher app), and press **Enter**.


### Step 3: Navigate to the Project Folder
Type `cd` followed by a space, then drag and drop the extracted project folder from your file manager directly into the Terminal/Command Prompt window, and press Enter:
```bash
cd /path/to/extracted/DataDiscrepancy
```

### Step 4: Run the Launcher Command

* **For macOS / Linux**:
  ```bash
  python3 __init__.py
  ```

* **For Windows**:
  ```bash
  python __init__.py
  ```

That's it! The launcher will download and install Poetry if it is missing, download Streamlit and other dependencies, and open the dashboard in your web browser automatically.


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
