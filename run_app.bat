@echo off
REM Change directory to script folder
cd /d %~dp0

REM Activate bundled venv (if you included one)
call venv\Scripts\activate.bat

REM Run Streamlit
python -m streamlit run app.py

pause