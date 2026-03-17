@echo off
cd /d "%~dp0"
echo Cleaning up unwanted test and temporary files...

del /f /q "test_*.py" 2>nul
del /f /q "temp_test_*.py" 2>nul
del /f /q "tmp_test_*.py" 2>nul
del /f /q "debug_*.py" 2>nul
del /f /q "check_*.py" 2>nul
del /f /q "diag_*.py" 2>nul
del /f /q "reproduce_err.py" 2>nul
del /f /q "verify_fix.py" 2>nul
del /f /q "final_line_test.py" 2>nul
del /f /q "run_test.bat" 2>nul
del /f /q "run_mt942.bat" 2>nul
del /f /q "check_server.bat" 2>nul
del /f /q "package-lock.json" 2>nul
del /f /q "startup_error.txt" 2>nul
del /f /q "schme_test_results.json" 2>nul
del /f /q "app\services\run_schme_test.py" 2>nul
del /f /q "')" 2>nul
del /f /q "'))" 2>nul
del /f /q "'" 2>nul

echo Cleaning up frontend temporary files...
del /f /q "..\iso20022generatorfrontend\build_err*.txt" 2>nul

echo Root cleanup...
del /f /q "..\startup_error.txt" 2>nul
del /f /q "..\final_cleanup_script.py" 2>nul
del /f /q "..\debug_cleanup.py" 2>nul

echo Cleanup complete!
pause
