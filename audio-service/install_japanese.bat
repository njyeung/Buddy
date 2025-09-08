@echo off
echo Installing Japanese language support for Coqui TTS...
echo.

REM Check if virtual environment is activated
if "%VIRTUAL_ENV%"=="" (
    echo ERROR: Virtual environment is not activated!
    echo Please run: venv\Scripts\activate
    echo Then run this script again.
    pause
    exit /b 1
)

echo Virtual environment detected: %VIRTUAL_ENV%
echo.

echo Installing Japanese dependencies...
echo.

echo [1/3] Installing cutlet (Japanese text processing)...
pip install cutlet>=0.1.0
if %errorLevel% neq 0 (
    echo Failed to install cutlet!
    pause
    exit /b 1
)

echo [2/3] Installing fugashi (Modern MeCab binding)...
pip install fugashi>=1.1.0
if %errorLevel% neq 0 (
    echo Failed to install fugashi!
    pause
    exit /b 1
)

echo [3/3] Installing unidic-lite (Japanese dictionary)...
pip install unidic-lite>=1.0.8
if %errorLevel% neq 0 (
    echo Failed to install unidic-lite!
    pause
    exit /b 1
)

echo.
echo ✓ All Japanese dependencies installed successfully!
echo.
echo You can now use Japanese language support in your voice cloning service.
echo Restart your service and try with Japanese text.
echo.

echo Test command:
echo curl -X POST http://127.0.0.1:8081/api/tts -H "Content-Type: application/json" -d "{\"text\": \"これは日本語の音声クローニングのテストです。\", \"voice\": \"custom\"}" --output test_japanese.wav
echo.

pause