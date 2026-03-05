import os
import shutil

files_to_delete = [
    "check_db_count.py",
    "check_server.bat",
    "check_sqlite.py",
    "cleanup.py",
    "debug_zip.py",
    "diag_extract.py",
    "extract_v2.py",
    "extract_xsds.py",
    "fix_deps.bat",
    "fix_deps_py.bat",
    "fix_log.txt",
    "fix_log_py.txt",
    "force_extract.py",
    "force_setup.py",
    "iso_validator.db",
    "list_camt.py",
    "list_zip.py",
    "run.py",
    "server_status.txt",
    "setup_xsds.py",
    "start_backend.bat",
    "startup_error.txt"
]

backend_dir = r"c:\Users\HP\Desktop\iso20022 Validator - Copy\backend"

for file_name in files_to_delete:
    file_path = os.path.join(backend_dir, file_name)
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
            print(f"Deleted file: {file_name}")
        elif os.path.isdir(file_path):
            shutil.rmtree(file_path)
            print(f"Deleted directory: {file_name}")
    except Exception as e:
        print(f"Error deleting {file_name}: {e}")

# Also check for app/models
models_dir = os.path.join(backend_dir, "app", "models")
if os.path.exists(models_dir):
    try:
        shutil.rmtree(models_dir)
        print("Deleted directory: app/models")
    except Exception as e:
        print(f"Error deleting app/models: {e}")
