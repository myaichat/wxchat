# PowerShell script to list currently running Streamlit apps and their ports
# Author: Generated for UI Interview Copilot project

Write-Host "=== Streamlit Apps Monitor ===" -ForegroundColor Green
Write-Host "Scanning for running Streamlit applications..." -ForegroundColor Yellow
Write-Host ""

try {
    # Find all Python processes that might be running Streamlit
    $pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue
    
    if (-not $pythonProcesses) {
        Write-Host "No Python processes found running." -ForegroundColor Red
        exit
    }
    
    $streamlitApps = @()
    
    foreach ($process in $pythonProcesses) {
        try {
            # Get command line arguments for the process
            $commandLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
            
            # Check if this is a Streamlit process
            if ($commandLine -and ($commandLine -like "*streamlit*" -or $commandLine -like "*-m streamlit*")) {
                # Get network connections for this process
                $connections = Get-NetTCPConnection -OwningProcess $process.Id -State Listen -ErrorAction SilentlyContinue
                
                $ports = @()
                foreach ($conn in $connections) {
                    if ($conn.LocalAddress -eq "0.0.0.0" -or $conn.LocalAddress -eq "::" -or $conn.LocalAddress -eq "127.0.0.1" -or $conn.LocalAddress -eq "::1") {
                        $ports += $conn.LocalPort
                    }
                }
                
                # Extract app file name from command line if possible
                $appFile = "Unknown"
                if ($commandLine -match "streamlit run\s+([^\s]+)") {
                    $appFile = $matches[1]
                } elseif ($commandLine -match "run\s+([^\s]+)") {
                    $appFile = $matches[1]
                }
                
                $streamlitApp = [PSCustomObject]@{
                    ProcessId = $process.Id
                    ProcessName = $process.ProcessName
                    AppFile = $appFile
                    Ports = $ports
                    CommandLine = $commandLine
                    StartTime = $process.StartTime
                }
                
                $streamlitApps += $streamlitApp
            }
        }
        catch {
            # Skip processes we can't access
            continue
        }
    }
    
    if ($streamlitApps.Count -eq 0) {
        Write-Host "No Streamlit applications found running." -ForegroundColor Yellow
    } else {
        Write-Host "Found $($streamlitApps.Count) Streamlit application(s):" -ForegroundColor Green
        Write-Host ""
        
        $counter = 1
        foreach ($app in $streamlitApps) {
            Write-Host "[$counter] Streamlit App Details:" -ForegroundColor Cyan
            Write-Host "  Process ID: $($app.ProcessId)" -ForegroundColor White
            Write-Host "  App File: $($app.AppFile)" -ForegroundColor White
            
            if ($app.Ports.Count -gt 0) {
                Write-Host "  Listening Ports: $($app.Ports -join ', ')" -ForegroundColor Green
                foreach ($port in $app.Ports) {
                    Write-Host "    -> http://localhost:$port" -ForegroundColor Magenta
                }
            } else {
                Write-Host "  Listening Ports: None detected" -ForegroundColor Red
            }
            
            Write-Host "  Started: $($app.StartTime)" -ForegroundColor White
            Write-Host "  Command: $($app.CommandLine)" -ForegroundColor Gray
            Write-Host ""
            $counter++
        }
        
        # Summary
        Write-Host "=== Quick Access URLs ===" -ForegroundColor Green
        foreach ($app in $streamlitApps) {
            if ($app.Ports.Count -gt 0) {
                foreach ($port in $app.Ports) {
                    $fileName = Split-Path $app.AppFile -Leaf
                    Write-Host "$fileName -> http://localhost:$port" -ForegroundColor Magenta
                }
            }
        }
    }
    
    # Additional check for common Streamlit ports even if process detection fails
    Write-Host ""
    Write-Host "=== Checking Common Streamlit Ports ===" -ForegroundColor Yellow
    $commonPorts = @(8501, 8502, 8503, 8504, 8505)
    
    foreach ($port in $commonPorts) {
        $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($connection) {
            $process = Get-Process -Id $connection.OwningProcess -ErrorAction SilentlyContinue
            if ($process) {
                Write-Host "Port $port is active (Process: $($process.ProcessName), PID: $($process.Id))" -ForegroundColor Green
            } else {
                Write-Host "Port $port is active (Unknown process)" -ForegroundColor Yellow
            }
        }
    }
}
catch {
    Write-Host "Error occurred: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host ""
Write-Host "Scan completed." -ForegroundColor Green
