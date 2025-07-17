# Kill Chrome Debug Process on Port 9222
# Standalone PowerShell script to terminate Chrome debugging session

Write-Host "Searching for Chrome process on port 9222..."

# Find Chrome process using port 9222
$port9222Process = netstat -ano | findstr ':9222' | findstr 'LISTENING'

if ($port9222Process) {
    # Extract PID from netstat output
    $chromePid = ($port9222Process -split '\s+')[-1]
    
    if ($chromePid) {
        # Verify this is actually a Chrome process before killing
        $processInfo = Get-Process -Id $chromePid -ErrorAction SilentlyContinue
        if ($processInfo -and $processInfo.ProcessName -eq "chrome") {
            Write-Host "Found Chrome process on port 9222 (PID: $chromePid)"
            
            # Kill the Chrome process
            try {
                taskkill /F /PID $chromePid 2>$null
                if ($LASTEXITCODE -eq 0) {
                    Write-Host "Successfully killed Chrome debug process (PID: $chromePid)"
                } else {
                    Write-Host "Process may have already been terminated or access denied"
                }
            } catch {
                Write-Host "Error killing process: $($_.Exception.Message)"
            }
            
            # Wait a moment for cleanup
            Start-Sleep -Seconds 1
            
            # Verify the process is gone
            $verifyProcess = netstat -ano | findstr ':9222' | findstr 'LISTENING'
            if (-not $verifyProcess) {
                Write-Host "Port 9222 is now free"
            } else {
                Write-Host "Port 9222 may still be in use"
            }
        } else {
            Write-Host "Process on port 9222 (PID: $chromePid) is not Chrome - skipping for safety"
        }
    } else {
        Write-Host "Could not extract PID from netstat output"
    }
} else {
    Write-Host "No Chrome process found listening on port 9222"
    Write-Host "Chrome debug mode may not be running"
}

Write-Host "Script completed"
