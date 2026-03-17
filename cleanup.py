import os
import glob
import shutil

def remove_file(filepath):
    if os.path.exists(filepath):
        try:
            os.remove(filepath)
            print(f"Deleted file: {filepath}")
        except Exception as e:
            print(f"Error deleting {filepath}: {e}")

# Relative paths from backend root
backend_patterns = [
    "test_*.py",
    "temp_test_*.py",
    "tmp_test_*.py",
    "debug_*.py",
    "check_*.py",
    "diag_*.py",
    "reproduce_err.py",
    "verify_fix.py",
    "final_line_test.py",
    "run_test.bat",
    "run_mt942.bat",
    "check_server.bat",
    "package-lock.json",
    "startup_error.txt",
    "schme_test_results.json",
    "'", "')", "'))"
]

specific_files = [
    "app/services/run_schme_test.py",
    "../iso20022generatorfrontend/build_err.txt",
    "../iso20022generatorfrontend/build_err2.txt",
    "../startup_error.txt"
]

print("Starting cleanup...")

for pattern in backend_patterns:
    for f in glob.glob(pattern):
        remove_file(f)

for f in specific_files:
    remove_file(f)

# Also clean __pycache__
for root, dirs, files in os.walk("."):
    for d in dirs:
        if d == "__pycache__":
            shutil.rmtree(os.path.join(root, d))
            print(f"Removed cache: {os.path.join(root, d)}")

print("Cleanup finished.")
