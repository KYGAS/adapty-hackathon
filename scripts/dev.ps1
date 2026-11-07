# Starts the backend (port 8010) and the frontend (port 5173) in two windows.
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\backend'; python -X utf8 -m referee"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "Set-Location '$root\frontend'; npm run dev"
Write-Host "Backend: http://localhost:8010/docs   Frontend: http://localhost:5173"
