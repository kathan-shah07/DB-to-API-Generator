import subprocess
import os
import sys
import ctypes
import shutil
import time

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def copy_bundle_to_target(source_base, target_dir):
    """Copies the bundled folders from _MEIPASS to the target installation directory."""
    folders_to_copy = ["backend", "frontend", "scripts", "demo", "setup"]
    files_to_copy = ["README.md", "Run_DB_to_API_Server.exe"]
    
    if not os.path.exists(target_dir):
        os.makedirs(target_dir)
        print(f"Created directory: {target_dir}")

    for folder in folders_to_copy:
        src = os.path.join(source_base, folder)
        dst = os.path.join(target_dir, folder)
        if os.path.exists(src):
            if os.path.exists(dst):
                shutil.rmtree(dst)
            shutil.copytree(src, dst)
            print(f"Copied {folder} to {dst}")

    for file in files_to_copy:
        src = os.path.join(source_base, file)
        dst = os.path.join(target_dir, file)
        if os.path.exists(src):
            shutil.copy2(src, dst)
            print(f"Copied {file} to {dst}")

def run_ps_script(script_path, project_root):
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
        print("Requesting Administrator privileges for system installations...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit()

    # 1. Determine where we are (temp folder vs current folder)
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    
    # 2. Set target installation directory (Current folder/DB_to_API_Generator)
    # This is where the code will live permanently
    install_dir = os.path.join(os.getcwd(), "DB_to_API_Generator")
    
    print("==========================================")
    print("   DB-to-API Generator Unified Installer   ")
    print("==========================================")
    print(f"\nTarget Directory: {install_dir}")
    
    try:
        # 3. Extract the codebase
        print("\n[*] Extracting codebase...")
        copy_bundle_to_target(base_path, install_dir)
        
        # 4. Run Pre-requisites (using the script we just extracted)
        print("\n[*] Installing system pre-requisites (Python, Node, ODBC)...")
        # Note: the script is now in install_dir/setup/install_prerequisites.ps1
        script_path = os.path.join(install_dir, "setup", "install_prerequisites.ps1")
        
        if os.path.exists(script_path):
            run_ps_script(script_path, install_dir)
        else:
            print(f"ERROR: Installer script not found at {script_path}")
            
        print("\n🎉 ALL DONE!")
        print(f"The application has been installed to: {install_dir}")
        print("You can now run 'Run_DB_to_API_Server.exe' (if bundled) or the UI script.")
        
    except Exception as e:
        print(f"\n❌ An error occurred during installation: {e}")
        
    print("\nYou can close this window now.")
    if sys.stdin and sys.stdin.isatty():
        input("Press Enter to exit...")
    else:
        time.sleep(10)
