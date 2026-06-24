import os
import subprocess
import sys
import shutil

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

def main():
    # Ensure current working directory is the project root containing this file
    project_root = os.path.dirname(os.path.abspath(__file__))
    os.chdir(project_root)
    
    print("=" * 60)
    print("Data Quality & Discrepancy Detection System - Launcher")
    print("=" * 60)
    print("[*] Checking system environment...")
    
    # 1. Check and install Poetry if missing
    poetry_cmd = get_poetry_command()
    if not poetry_cmd:
        print("[!] Poetry is not installed on this system.")
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
    
    # 2. Run poetry install to check and install/update dependencies
    print("[*] Checking and installing project packages (pandas, streamlit, etc.)...")
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

