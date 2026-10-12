@echo off
rem Review app for the Blackwall plates; the code is shared with C:\dev\koch, PLATE_PROJECT points it here
rem Re-run this file with stdin from NUL so Ctrl+C does not ask "Terminate batch job (Y/N)?"
if not defined REVIEW_NUL (set "REVIEW_NUL=1" & call <nul "%~f0" %* & exit /b)
set "PLATE_PROJECT=%~dp0."
start "" /b cmd /c "timeout /t 2 >nul & start http://localhost:8778"
C:\dev\koch\.venv\Scripts\python.exe -I C:\dev\koch\scripts\review_app.py 8778
