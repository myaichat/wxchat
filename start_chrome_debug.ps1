# Kill all running Chrome processes
taskkill /F /IM chrome.exe 2>$null

# Start Chrome with remote debugging in a new process
$chromeArgs = @(
    "--remote-debugging-port=9222",
    "--user-data-dir=chrome-debug",
    "--disable-background-timer-throttling",
    "--disable-renderer-backgrounding",
    "--disable-backgrounding-occluded-windows"
)

Start-Process -FilePath "C:\Program Files\Google\Chrome\Application\chrome.exe" -ArgumentList $chromeArgs

# Wait for port 9222 to open (up to 10 seconds)
$timeout = 20
$counter = 0
while (-not (netstat -an | findstr ':9222') -and $counter -lt $timeout) {
    Start-Sleep -Milliseconds 500
    $counter++
}

if ($counter -lt $timeout) {
    Write-Host "✅ Port 9222 is now open."
    
    # Wait a bit more for Chrome to fully initialize
    Start-Sleep -Seconds 2
    
    # Get the WebSocket debugger URL
    try {
        $response = curl -s http://localhost:9222/json
        if ($response) {
            $jsonData = $response | ConvertFrom-Json
            if ($jsonData.Count -gt 1) {
                $webSocketUrl = $jsonData[1].webSocketDebuggerUrl
                Write-Host "🔗 WebSocket Debugger URL: $webSocketUrl"
            } else {
                Write-Host "⚠️  Not enough tabs/pages available. WebSocket URL: $($jsonData[0].webSocketDebuggerUrl)"
            }
        } else {
            Write-Host "❌ Failed to get response from Chrome debugging endpoint."
        }
    } catch {
        Write-Host "❌ Error retrieving WebSocket URL: $($_.Exception.Message)"
        Write-Host "💡 You can manually check: http://localhost:9222/json"
    }
} else {
    Write-Host "❌ Port 9222 did not open in time."
}
