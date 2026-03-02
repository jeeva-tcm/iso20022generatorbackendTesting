@echo off
cd "c:\Users\HP\Desktop\iso20022 Validator - Copy\backend"
del /f /q check_db_count.py
del /f /q check_server.bat
del /f /q check_sqlite.py
del /f /q cleanup.py
del /f /q debug_zip.py
del /f /q diag_extract.py
del /f /q extract_v2.py
del /f /q extract_xsds.py
del /f /q fix_deps.bat
del /f /q fix_deps_py.bat
del /f /q fix_log.txt
del /f /q fix_log_py.txt
del /f /q force_extract.py
del /f /q force_setup.py
del /f /q iso_validator.db
del /f /q list_camt.py
del /f /q list_zip.py
del /f /q run.py
del /f /q server_status.txt
del /f /q setup_xsds.py
del /f /q start_backend.bat
del /f /q startup_error.txt
rmdir /s /q app\models
echo Cleanup complete.
