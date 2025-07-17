# Kill all running python processes
taskkill /F /IM python.exe

# Start the streaming server in a new cmd window
Start-Process cmd -ArgumentList "/k", "python streaming_server.py"

# Wait for port 8002 to open (up to 10 seconds)
$timeout = 20
$counter = 0
while (-not (netstat -an | findstr ':8002') -and $counter -lt $timeout) {
    Start-Sleep -Milliseconds 500
    $counter++
}

if ($counter -lt $timeout) {
    Write-Host "✅ Port 8002 is now open."
} else {
    Write-Host "❌ Port 8002 did not open in time."
}
