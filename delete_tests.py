import os, glob

files_to_remove = []
files_to_remove.extend(glob.glob("*test*.py"))
files_to_remove.extend(glob.glob("test*"))
files_to_remove.extend(glob.glob("tmp*"))
files_to_remove.extend(glob.glob("../frontend/*build_err*"))
files_to_remove.append("output.txt")
files_to_remove.append("test_out.txt")

for f in set(files_to_remove):
    if os.path.exists(f) and os.path.isfile(f):
        try:
            os.remove(f)
            print(f"Successfully deleted {f}")
        except Exception as e:
            print(f"Error deleting {f}: {e}")
