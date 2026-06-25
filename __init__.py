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

def install_64bit_python_without_admin() -> str:
    """
    Downloads and installs Python 3.9.13 64-bit silently for the current user (no admin rights needed).
    Returns the path to the installed python executable if successful, or None.
    """
    url = "https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe"
    print("[*] Downloading Python 3.9.13 (64-bit) installer...")
    print(f"    From: {url}")
    
    try:
        temp_dir = tempfile.gettempdir()
        installer_path = os.path.join(temp_dir, "python-3.9.13-amd64.exe")
        
        # Download the installer using urllib with a User-Agent header and ignoring SSL errors for corporate proxies
        context = ssl._create_unverified_context()
        req = urllib.request.Request(
            url, 
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        )
        with urllib.request.urlopen(req, context=context) as response, open(installer_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
            
        print("[+] Download complete.")
        
        print("[*] Installing Python 3.9.13 (64-bit) silently for the current user...")
        # Run installer silently for the current user:
        # InstallAllUsers=0 (no admin required)
        # PrependPath=1 (add to user PATH)
        # /quiet (silent install)
        # AssociateFiles=0 Shortcuts=0 (reduce installer footprint)
        result = subprocess.run([
            installer_path,
            "/quiet",
            "InstallAllUsers=0",
            "PrependPath=1",
            "AssociateFiles=0",
            "Shortcuts=0"
        ])
        
        if result.returncode == 0:
            print("[+] Python 3.9.13 (64-bit) installed successfully!")
            
            # Check user install path
            local_app_data = os.environ.get("LOCALAPPDATA", "")
            if local_app_data:
                user_py_path = os.path.join(local_app_data, "Programs", "Python", "Python39", "python.exe")
                if os.path.exists(user_py_path):
                    return user_py_path
            
            # Fallback glob search in user profile
            user_profile = os.environ.get("USERPROFILE", "")
            if user_profile:
                search_pattern = os.path.join(user_profile, "AppData", "Local", "Programs", "Python", "Python3*", "python.exe")
                matches = glob.glob(search_pattern)
                if matches:
                    return matches[0]
        else:
            print(f"[-] Error: Installer exited with code {result.returncode}", file=sys.stderr)
            
    except Exception as e:
        print(f"[-] Error: Failed to download or install Python silently: {e}", file=sys.stderr)
        
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
        if not ask_permission("[?] Do you want to download and install 64-bit Python 3.9 silently now (no admin rights required)?"):
            print("[-] ERROR: Python 64-bit installation disallowed by user. Exiting.", file=sys.stderr)
            sys.exit(1)
            
        print("[*] Attempting user-level silent installation of 64-bit Python 3.9...")
        py64 = install_64bit_python_without_admin()
        if py64:
            print(f"[+] Successfully installed 64-bit Python: {py64}")
            print(f"Restarting with {py64}")
            subprocess.run([py64] + sys.argv)
            sys.exit()
        else:
            print("[-] ERROR: Failed to install or locate 64-bit Python.", file=sys.stderr)
            print("    Please manually download and install 64-bit Python 3 from:", file=sys.stderr)
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
