@echo off
echo Starting Supervity Docker containers...
docker-compose up -d --build
echo.
echo Docker containers are now running in the background.
echo Backend is available at http://localhost:8001
echo Frontend is available at http://localhost:3001
echo.
echo To view logs, run: docker-compose logs -f
echo To stop containers, run: stop_docker.bat
pause
