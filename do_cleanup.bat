@echo off
echo Deleting files... > cleanup_trace.txt
del /f /q "test_*.py" >> cleanup_trace.txt 2>&1
del /f /q "temp_test_*.py" >> cleanup_trace.txt 2>&1
del /f /q "tmp_test_*.py" >> cleanup_trace.txt 2>&1
del /f /q "debug_*.py" >> cleanup_trace.txt 2>&1
del /f /q "check_*.py" >> cleanup_trace.txt 2>&1
del /f /q "diag_*.py" >> cleanup_trace.txt 2>&1
del /f /q "reproduce_err.py" >> cleanup_trace.txt 2>&1
del /f /q "verify_fix.py" >> cleanup_trace.txt 2>&1
del /f /q "final_line_test.py" >> cleanup_trace.txt 2>&1
del /f /q "run_test.bat" >> cleanup_trace.txt 2>&1
del /f /q "run_mt942.bat" >> cleanup_trace.txt 2>&1
del /f /q "check_server.bat" >> cleanup_trace.txt 2>&1
del /f /q "cleanup.py" >> cleanup_trace.txt 2>&1
del /f /q "cleanup.bat" >> cleanup_trace.txt 2>&1
del /f /q "cleanup_temp.py" >> cleanup_trace.txt 2>&1
del /f /q "delete_tests.py" >> cleanup_trace.txt 2>&1
del /f /q "package-lock.json" >> cleanup_trace.txt 2>&1
del /f /q "startup_error.txt" >> cleanup_trace.txt 2>&1
del /f /q "schme_test_results.json" >> cleanup_trace.txt 2>&1
del /f /q "')" >> cleanup_trace.txt 2>&1
del /f /q "'))" >> cleanup_trace.txt 2>&1
del /f /q "'" >> cleanup_trace.txt 2>&1
echo Done. >> cleanup_trace.txt
