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
