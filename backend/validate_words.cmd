@echo off
REM Validate words from any text file (one word per line).
REM Outputs: <input_stem>_valid.txt and <input_stem>_invalid.txt
REM Requires backend\.env with NHOST_DATABASE_URL for database saves.
cd /d "%~dp0"

REM Example — invalid word list (re-validate suspected invalid words):
REM   validate_words.cmd --fresh --api exhaust-all --input invalid_words_invalid.txt --concurrency 3 --batch-size 25 --batch-delay 2
REM
REM Example — valid word list (confirm + enrich in Nhost):
REM   validate_words.cmd --fresh --api exhaust-all --input invalid_words_valid.txt --concurrency 3 --batch-size 25 --batch-delay 2
REM
REM Resume after interrupt (same --input and --api, omit --fresh):
REM   validate_words.cmd --api exhaust-all --input invalid_words_invalid.txt --concurrency 3 --batch-size 25 --batch-delay 2

venv\Scripts\python.exe validate_words.py %*
