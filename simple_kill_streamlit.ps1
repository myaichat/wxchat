# Simple script to kill Streamlit processes
Write-Host "Killing Streamlit processes..." -ForegroundColor Red

$killed = 0
Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object {
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    if ($cmd -like "*streamlit*") {
        Write-Host "Killing PID $($_.Id)" -ForegroundColor Yellow
        try {
            Stop-Process -Id $_.Id -Force
            $killed++
            Write-Host "Killed PID $($_.Id)" -ForegroundColor Green
        }
        catch {
            Write-Host "Failed to kill PID $($_.Id)" -ForegroundColor Red
        }
    }
}

Write-Host "Killed $killed Streamlit processes" -ForegroundColor Green
