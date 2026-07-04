@echo off
cd /d "%~dp0"
venv\Scripts\python.exe scripts\import_words_to_nhost.py %*
