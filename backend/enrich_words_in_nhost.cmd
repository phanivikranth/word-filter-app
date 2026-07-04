@echo off
cd /d "%~dp0.."
call venv\Scripts\python.exe scripts\enrich_words_in_nhost.py %*
