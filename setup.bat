@echo off
REM Quick setup script for botchat (Windows)

echo.
echo  botchat Setup
echo ==========================
echo.

REM Check for Git and fix line endings
where git >nul 2>nul
if %ERRORLEVEL% EQU 0 (
    echo Checking git configuration...
    for /f %%i in ('git config core.autocrlf') do set AUTOCRLF=%%i
    if "!AUTOCRLF!"=="true" (
        echo ⚠ Git autocrlf is enabled - this breaks Docker builds on Windows
        echo   Fixing: git config core.autocrlf false
        git config core.autocrlf false
        echo √ Fixed
        echo.
    )
    REM Force normalize line endings to LF
    echo Normalizing line endings to LF for Docker...
    git add --renormalize -A
    if %ERRORLEVEL% EQU 0 (
        echo √ Line endings normalized
        echo.
    )
) else (
    echo X Git is not installed. Please install Git from: https://git-scm.com/
    pause
    exit /b 1
)

REM Check for Docker
where docker >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo X Docker is not installed.
    echo    Please install Docker Desktop from: https://www.docker.com/products/docker-desktop/
    pause
    exit /b 1
)

docker info >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo X Docker is not running. Please start Docker Desktop.
    pause
    exit /b 1
)

echo √ Docker is ready
echo.

REM Create .env if it doesn't exist
if not exist .env (
    echo Creating .env file...
    
    REM Generate random API key using PowerShell
    for /f %%i in ('powershell -Command "[Convert]::ToHexString([Security.Cryptography.RandomNumberGenerator]::GetBytes(32)).ToLower()"') do set API_KEY=%%i
    
    (
        echo # Auto-generated shared secret ^(do not change unless you know what you're doing^)
        echo API_KEY=%API_KEY%
        echo.
        echo # Optional: Pre-configure AI provider keys here, or add them via Settings UI
        echo # OPENAI_API_KEY=sk-your-key
        echo # GOOGLE_API_KEY=your-key
        echo.
        echo # Logging level ^(WARNING, INFO, DEBUG^)
        echo LOG_LEVEL=WARNING
    ) > .env
    
    echo √ Generated secure API_KEY
    echo.
    echo Setup complete! Starting application...
    echo.
)

docker compose up --build

echo.
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo  Open http://localhost:3000 in your browser
echo  Click the gear icon to add your API keys
echo ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

pause
