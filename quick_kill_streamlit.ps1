# Quick kill all Streamlit apps - one liner with verification
Get-Process python* -ErrorAction SilentlyContinue | Where-Object { 
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    $cmd -like "*streamlit*"
} | ForEach-Object { 
    Write-Host "Force killing Streamlit app (PID: $($_.Id))" -ForegroundColor Red
    try {
        Stop-Process -Id $_.Id -Force -ErrorAction Stop
        Start-Sleep -Milliseconds 300
        $check = Get-Process -Id $_.Id -ErrorAction SilentlyContinue
        if ($check) {
            Write-Host "⚠ Process $($_.Id) still running - trying again" -ForegroundColor Yellow
            Stop-Process -Id $_.Id -Force -ErrorAction Stop
        } else {
            Write-Host "✓ Process $($_.Id) terminated" -ForegroundColor Green
        }
    }
    catch {
        Write-Host "✗ Failed to kill process $($_.Id): $($_.Exception.Message)" -ForegroundColor Red
    }
}
