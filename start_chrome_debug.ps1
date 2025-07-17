# Use a different port to avoid conflicts
$debugPort = 9223

# Kill only Chrome process using the debug port
$portProcess = netstat -ano | findstr ":$debugPort" | findstr 'LISTENING'
if ($portProcess) {
    $pid = ($portProcess -split '\s+')[-1]
    if ($pid) {
        Write-Host "Killing Chrome process on port $debugPort (PID: $pid)"
        taskkill /F /PID $pid 2>$null
        Start-Sleep -Seconds 1
    }
} else {
    Write-Host "No Chrome process found on port $debugPort"
}

# Remove existing debug directory to avoid conflicts
$debugDir = "chrome-debug-$debugPort"
if (Test-Path $debugDir) {
    Write-Host "Removing existing debug directory..."
    Remove-Item -Recurse -Force $debugDir -ErrorAction SilentlyContinue
}

# Start Chrome with remote debugging in a new process
$chromeArgs = @(
    "--remote-debugging-port=$debugPort",
    "--user-data-dir=$debugDir",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows",
    "--no-first-run",
    "--disable-default-apps"
)

Write-Host "Starting Chrome with debugging enabled..."
Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList $chromeArgs

# Wait for debug port to open (up to 20 seconds)
$timeout = 40
$counter = 0
Write-Host "Waiting for port $debugPort to open..."
while (-not (netstat -an | findstr ":$debugPort") -and $counter -lt $timeout) {
    Start-Sleep -Milliseconds 500
    $counter++
    if ($counter % 4 -eq 0) {
        Write-Host "Still waiting... ($($counter/2) seconds elapsed)"
    }
}

if ($counter -ge $timeout) {
    Write-Host "Port $debugPort did not open in time after $($timeout/2) seconds."
    Write-Host "Chrome may have failed to start or is taking longer than expected."
    exit
}

Write-Host "Port $debugPort is now open."

# Wait a bit more for Chrome to fully initialize
Start-Sleep -Seconds 2

# Get the WebSocket debugger URL
$response = Invoke-RestMethod -Uri "http://localhost:$debugPort/json" -Method Get -ErrorAction SilentlyContinue

if ($response -and $response.Count -gt 0) {
    if ($response.Count -gt 1) {
        $webSocketUrl = $response[1].webSocketDebuggerUrl
        Write-Host "WebSocket Debugger URL: $webSocketUrl"
    } else {
        $webSocketUrl = $response[0].webSocketDebuggerUrl
        Write-Host "Only one tab/page available. WebSocket URL: $webSocketUrl"
    }
} else {
    Write-Host "Error retrieving WebSocket URL or no response from Chrome debugging endpoint."
    Write-Host "You can manually check: http://localhost:$debugPort/json"
}
