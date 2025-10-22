@echo off
REM Helper script untuk development dan testing (Windows)

if "%1"=="" goto help
if "%1"=="install" goto install
if "%1"=="test" goto test
if "%1"=="run" goto run
if "%1"=="docker-build" goto docker_build
if "%1"=="docker-run" goto docker_run
if "%1"=="docker-compose" goto docker_compose
if "%1"=="clean" goto clean
goto help

:help
echo UTS Log Aggregator - Development Helper
echo.
echo Usage: run.bat [command]
echo.
echo Commands:
echo   install        - Install Python dependencies
echo   test           - Run all tests
echo   run            - Run application locally
echo   docker-build   - Build Docker image
echo   docker-run     - Run Docker container
echo   docker-compose - Run with Docker Compose
echo   clean          - Clean cache and data
goto end

:install
echo Installing dependencies...
pip install -r requirements.txt
echo Done!
goto end

:test
echo Running tests...
pytest tests/ -v --cov=src --cov-report=html
echo.
echo Coverage report generated in htmlcov/index.html
goto end

:run
echo Starting application...
python -m src.main
goto end

:docker_build
echo Building Docker image...
docker build -t uts-aggregator .
echo Done!
goto end

:docker_run
echo Running Docker container...
docker run -p 8080:8080 -v %cd%\data:/app/data uts-aggregator
goto end

:docker_compose
echo Starting services with Docker Compose...
docker-compose up --build
goto end

:clean
echo Cleaning cache and data...
if exist __pycache__ rmdir /s /q __pycache__
if exist src\__pycache__ rmdir /s /q src\__pycache__
if exist tests\__pycache__ rmdir /s /q tests\__pycache__
if exist .pytest_cache rmdir /s /q .pytest_cache
if exist htmlcov rmdir /s /q htmlcov
if exist .coverage del .coverage
if exist data rmdir /s /q data
echo Done!
goto end

:end
