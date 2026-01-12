import subprocess
import os
import sys
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_ps_script(script_path, project_root):
    # Construct the powershell command
    # We pass the project_root as a parameter to the PS script
    cmd = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-File", script_path,
        "-ProjectRoot", project_root
    ]
    
    print(f"Executing: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)

if __name__ == "__main__":
    if not is_admin():
        # Re-run the script with admin privileges
        print("Requesting Administrator privileges...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    # Get the path to the bundled script
    # PyInstaller stores data in _MEIPASS when running as a bundled exe
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    script_name = "install_prerequisites.ps1"
    script_path = os.path.join(base_path, script_name)

    if not os.path.exists(script_path):
        # Fallback to local directory if not found in bundle
        script_path = os.path.join(os.getcwd(), script_name)

    # Determine the actual project root (where the EXE is located)
    # If the EXE is in 'dist/', the root is one level up
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if os.path.basename(exe_dir).lower() == "dist":
        project_root = os.path.dirname(exe_dir)
    else:
        project_root = exe_dir

    print(f"Detected Project Root: {project_root}")
    print(f"Starting Installer from {script_path}...")
    
    try:
        run_ps_script(script_path, project_root)
    except Exception as e:
        print(f"An error occurred: {e}")
        # Only try to read input if we have a console
        if sys.stdin and sys.stdin.isatty():
            input("Press Enter to exit...")
        else:
            # Fallback for non-console/redirected output
            import time
            time.sleep(10)
