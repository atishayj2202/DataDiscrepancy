import os
import subprocess
import sys
import shutil
import glob
import platform
import urllib.request
import tempfile
import ssl

def is_64bit_python():
    return platform.architecture()[0] == "64bit"

def find_64bit_python():
    # Use the Python launcher to list installed versions
    try:
        output = subprocess.check_output(
            ["py", "-0p"],
            text=True,
            stderr=subprocess.STDOUT
        )

        for line in output.splitlines():
            # Example:
            # -V:3.9 * C:\Python39\python.exe
            if any(v in line for v in ["Python39", "3.9", "3.10", "3.11", "3.12", "3.13"]):
                path = line.split()[-1]
                if os.path.exists(path):
                    arch = subprocess.check_output(
                        [path, "-c", "import platform; print(platform.architecture()[0])"],
                        text=True
                    ).strip()

                    if arch == "64bit":
                        return path
    except Exception:
        # Fallback: Search common 64-bit Python installation directories in Program Files
        for path in glob.glob("C:/Program Files/Python3*/python.exe") + glob.glob("C:/Program Files/Python 3*/python.exe"):
            if os.path.exists(path):
                try:
                    arch = subprocess.check_output(
                        [path, "-c", "import platform; print(platform.architecture()[0])"],
                        text=True
                    ).strip()
                    if arch == "64bit":
                        return path
                except Exception:
                    pass

        # Fallback 2: Check user AppData local programs
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        if local_app_data:
            for path in glob.glob(os.path.join(local_app_data, "Programs", "Python", "Python3*", "python.exe")):
                if os.path.exists(path):
                    try:
                        arch = subprocess.check_output(
                            [path, "-c", "import platform; print(platform.architecture()[0])"],
                            text=True
                        ).strip()
                        if arch == "64bit":
                            return path
                    except Exception:
                        pass

    return None

def find_pyenv_via_pip_show() -> str:
    """
    Runs pip show pyenv-win, parses the 'Location:' field,
    and returns the path to pyenv.bat inside pyenv-win/bin.
    Raises ValueError if pyenv-win is not installed or Location is missing.
    """
    result = subprocess.run(
        [sys.executable, "-m", "pip", "show", "pyenv-win"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    if result.returncode != 0:
        raise ValueError("pyenv-win is not installed (pip show returned non-zero exit code).")
        
    location = None
    for line in result.stdout.splitlines():
        if line.startswith("Location:"):
            location = line.split(":", 1)[1].strip()
            break
            
    if not location:
        raise ValueError("Could not find 'Location:' field in pip show output.")
        
    # Construct the path to the executable inside pyenv-win/bin
    pyenv_bat = os.path.join(location, "pyenv-win", "bin", "pyenv.bat")
    if os.path.exists(pyenv_bat):
        return pyenv_bat
        
    pyenv_vbs = os.path.join(location, "pyenv-win", "bin", "pyenv.vbs")
    if os.path.exists(pyenv_vbs):
        return pyenv_vbs
        
    raise ValueError(f"pyenv-win was found at {location}, but pyenv.bat was not found in 'pyenv-win/bin'.")

def install_64bit_python_without_admin() -> str:
    """
    Installs Python 3.9.16 (64-bit) silently for the current user using pyenv-win (no admin rights needed).
    Returns the path to the installed python executable if successful, or None.
    """
    print("[*] Running pip install for pyenv-win...")
    try:
        # Run pip install pyenv-win. If already installed, pip will state "Requirement already satisfied"
        subprocess.run([sys.executable, "-m", "pip", "install", "pyenv-win"], check=True)
        print("[+] pip install command executed successfully.")
    except Exception as e:
        print(f"[-] Error executing pip install pyenv-win: {e}", file=sys.stderr)
        return None

    print("[*] Locating pyenv-win path using pip show...")
    try:
        pyenv_exe = find_pyenv_via_pip_show()
        print(f"[+] Found pyenv executable: {pyenv_exe}")
    except Exception as e:
        print(f"[-] ERROR: {e}", file=sys.stderr)
        sys.exit(1)

    print("[*] Running command line installation for Python 3.9.16...")
    try:
        # Run pyenv install 3.9.16
        subprocess.run([pyenv_exe, "install", "3.9.16"], check=True)
        print("[+] Python 3.9.16 (64-bit) installation command completed successfully.")
        
        # Locate the installed Python 3.9.16 path
        user_profile = os.environ.get("USERPROFILE", "")
        if user_profile:
            py39_path = os.path.join(user_profile, ".pyenv", "pyenv-win", "versions", "3.9.16", "python.exe")
            if os.path.exists(py39_path):
                return py39_path
            
            # Dynamic search fallback in versions dir
            versions_dir = os.path.join(user_profile, ".pyenv", "pyenv-win", "versions")
            if os.path.exists(versions_dir):
                search_pattern = os.path.join(versions_dir, "3.9.16*", "python.exe")
                matches = glob.glob(search_pattern)
                if matches:
                    return matches[0]
    except Exception as e:
        print(f"[-] Error installing Python 3.9.16 via pyenv: {e}", file=sys.stderr)

    return None

def get_poetry_command():
    """
    Checks if Poetry is available, first trying 'python -m poetry'
    and then checking for a global 'poetry' command.
    Returns the command list prefix (e.g., [sys.executable, '-m', 'poetry'] or ['poetry'])
    or None if not found.
    """
    # 1. Try 'python -m poetry'
    try:
        result = subprocess.run([sys.executable, "-m", "poetry", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if result.returncode == 0:
            return [sys.executable, "-m", "poetry"]
    except Exception:
        pass
        
    # 2. Try global 'poetry' command
    poetry_path = shutil.which("poetry")
    if poetry_path:
        try:
            result = subprocess.run([poetry_path, "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if result.returncode == 0:
                return [poetry_path]
        except Exception:
            pass
            
    return None

def ask_permission(question: str) -> bool:
    """
    Asks the user for confirmation (y/n).
    Returns True if user allows, False otherwise.
    """
    try:
        val = input(f"{question} (y/n): ").strip().lower()
        return val in ("y", "yes")
    except (KeyboardInterrupt, EOFError):
        print()
        return False

def main():
    # Ensure current working directory is the project root containing this file
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    # 0. Check for Windows OS architecture
    if os.name == 'nt':
        import platform
        machine = platform.machine().upper()
        arch = os.environ.get("PROCESSOR_ARCHITECTURE", "").upper()
        wow64 = os.environ.get("PROCESSOR_ARCHITEW6432", "").upper()
        is_64bit_os = "64" in machine or "64" in arch or "64" in wow64
        
        if not is_64bit_os:
            print("=" * 60)
            print("[-] ERROR: Need atleast 64 bit system")
            print("    PyArrow/Streamlit dependencies are incompatible with 32-bit Windows.")
            print("=" * 60)
            sys.exit(1)

    # 0.5 Check for 32-bit Python on 64-bit Windows hardware
    if os.name == 'nt' and not is_64bit_python():
        print("=" * 60)
        print("[!] Warning: You are running this script using a 32-bit Python.")
        print("    PyArrow (required by Streamlit) only supports 64-bit Windows.")
        print("=" * 60)

        py64 = find_64bit_python()
        if py64:
            print(f"Restarting with {py64}")
            subprocess.run([py64] + sys.argv)
            sys.exit()
        
        print("64-bit Python not found")
        if not ask_permission("[?] Do you want to download and install 64-bit Python 3.9.16 silently now (no admin rights required)?"):
            print("[-] ERROR: Python 64-bit installation disallowed by user. Exiting.", file=sys.stderr)
            sys.exit(1)
            
        print("[*] Attempting user-level silent installation of 64-bit Python 3.9.16...")
        py64 = install_64bit_python_without_admin()
        if py64:
            print(f"[+] Successfully installed 64-bit Python: {py64}")
            print(f"Restarting with {py64}")
            subprocess.run([py64] + sys.argv)
            sys.exit()
        else:
            print("[-] ERROR: Failed to install or locate 64-bit Python.", file=sys.stderr)
            print("    Please manually download and install 64-bit Python 3.9.16 or newer from:", file=sys.stderr)
            print("    https://www.python.org/downloads/ (Check 'Add python.exe to PATH' during installation)", file=sys.stderr)
            sys.exit(1)

    print("=" * 60)
    print("Data Quality & Discrepancy Detection System - Launcher")
    print("=" * 60)
    print("\n\n[*] Checking system environment...")
    
    # 1. Check and install Poetry if missing
    poetry_cmd = get_poetry_command()
    if not poetry_cmd:
        print("[!] Poetry is not installed on this system.")
        if not ask_permission("[?] Do you want to install Poetry automatically via pip?"):
            print("[-] ERROR: Poetry installation disallowed by user. Exiting.", file=sys.stderr)
            sys.exit(1)
            
        print("[*] Installing Poetry automatically via pip...")
        try:
            # Install poetry
            subprocess.run([sys.executable, "-m", "pip", "install", "poetry"], check=True)
            # Recheck
            poetry_cmd = get_poetry_command()
            if not poetry_cmd:
                print("[-] Error: Installed Poetry but failed to verify path.", file=sys.stderr)
                sys.exit(1)
            print("[+] Poetry successfully installed!")
        except subprocess.CalledProcessError as e:
            print(f"[-] Error: Failed to install Poetry automatically: {e}", file=sys.stderr)
            print("    Please install Poetry manually or run in a python environment with pip access.", file=sys.stderr)
            sys.exit(1)
            
    print(f"[+] Using Poetry command: {' '.join(poetry_cmd)}")
    
    # 1.5 Configure Poetry virtualenvs.use-poetry-python
    print("[*] Configuring Poetry to use current environment python...")
    try:
        subprocess.run(poetry_cmd + ["config", "virtualenvs.use-poetry-python", "true"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"[!] Warning: Failed to configure Poetry use-poetry-python (exit code: {e.returncode}). Proceeding...")
    
    # 2. Run poetry install to check and install/update dependencies
    print("[*] Checking project packages (pandas, streamlit, etc.)...")
    print("[*] Running 'poetry install' to synchronize packages...")
    try:
        # We run poetry install to ensure all required packages are present in the virtual environment
        result = subprocess.run(poetry_cmd + ["install"], check=True)
        if result.returncode == 0:
            print("[+] Packages checked and successfully installed/updated.")
    except subprocess.CalledProcessError as e:
        print(f"[-] Error: Failed to run 'poetry install' (exit code: {e.returncode}).", file=sys.stderr)
        sys.exit(e.returncode)
        
    # 3. Launch the Streamlit application
    print("[*] Launching Streamlit dashboard...")
    streamlit_cmd = poetry_cmd + ["run", "streamlit", "run", "src/app.py"]
    try:
        # Run streamlit in the foreground so the user sees the output and can terminate it with Ctrl+C
        subprocess.run(streamlit_cmd)
    except KeyboardInterrupt:
        print("\n[+] Streamlit dashboard stopped by user.")
    except Exception as e:
        print(f"[-] Error: Failed to start Streamlit dashboard: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
