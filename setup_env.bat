@echo off
echo Setting up environment for Sign Language Recognition...

py -3.10 --version
IF %ERRORLEVEL% NEQ 0 (
    echo Python 3.10 not found! Please install Python 3.10 from https://www.python.org/downloads/
    pause
    exit /b
)

echo Creating virtual environment...
py -3.10 -m venv venv
call venv\Scripts\activate

echo Upgrading pip...
python -m pip install --upgrade pip

echo Installing dependencies...
pip install -r requirements.txt

echo Setup complete! You can now run the app with:
echo venv\Scripts\python main.py
pause
