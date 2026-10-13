@echo off
rem Build the gallery into site\ (settings in data\site.json); the code is shared with C:\dev\koch
set "PLATE_PROJECT=%~dp0."
C:\dev\koch\.venv\Scripts\python.exe -I C:\dev\koch\scripts\poster.py %*
