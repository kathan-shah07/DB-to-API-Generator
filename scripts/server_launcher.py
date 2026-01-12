import subprocess
import os
import sys

def run_ps_script(script_path, project_root):
    # Construct the powershell command to run the UI
    cmd = [
        "powershell.exe",
        "-ExecutionPolicy", "Bypass",
        "-File", script_path
    ]
    
    print(f"Launching Server from: {project_root}")
    print(f"Executing: {' '.join(cmd)}")
    
    # Start the process in the project root directory
    subprocess.run(cmd, cwd=project_root, check=True)

if __name__ == "__main__":
    # Determine the project root (where the EXE is located)
    # If the EXE is in 'dist/', the root is one level up
    exe_dir = os.path.dirname(os.path.abspath(sys.executable))
    if os.path.basename(exe_dir).lower() == "dist":
        project_root = os.path.dirname(exe_dir)
    else:
        project_root = exe_dir

    script_name = "run_ui.ps1"
    script_path = os.path.join(project_root, "setup", script_name)

    if not os.path.exists(script_path):
        print(f"ERROR: Could not find {script_name} at {script_path}")
        import time
        time.sleep(10)
        sys.exit(1)

    try:
        run_ps_script(script_path, project_root)
    except Exception as e:
        print(f"An error occurred: {e}")
        if sys.stdin and sys.stdin.isatty():
            input("Press Enter to exit...")
        else:
            import time
            time.sleep(10)
