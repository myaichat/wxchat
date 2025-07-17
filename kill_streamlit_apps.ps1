# PowerShell script to kill running Streamlit applications
# Author: Generated for UI Interview Copilot project

param(
    [switch]$Force,
    [switch]$List,
    [switch]$Help,
    [int]$ProcessId
)

if ($Help) {
    Write-Host @"
Kill Streamlit Apps - Terminate running Streamlit applications

Usage: .\kill_streamlit_apps.ps1 [-Force] [-List] [-ProcessId <processid>] [-Help]

Options:
  -Force         Kill all Streamlit apps without confirmation
  -List          List running Streamlit apps without killing them
  -ProcessId <id> Kill specific Streamlit app by Process ID
  -Help          Show this help message

Examples:
  .\kill_streamlit_apps.ps1                # Interactive mode with confirmation
  .\kill_streamlit_apps.ps1 -Force         # Kill all without confirmation
  .\kill_streamlit_apps.ps1 -List          # Just list running apps
  .\kill_streamlit_apps.ps1 -ProcessId 1234 # Kill specific process
"@ -ForegroundColor Green
    exit
}

function Get-StreamlitProcesses {
    $streamlitProcesses = @()
    
    $pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue
    
    foreach ($process in $pythonProcesses) {
        try {
            $commandLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
            
            if ($commandLine -and ($commandLine -like "*streamlit*" -or $commandLine -like "*-m streamlit*")) {
                # Get listening ports
                $connections = Get-NetTCPConnection -OwningProcess $process.Id -State Listen -ErrorAction SilentlyContinue
                $ports = $connections | Where-Object { 
                    $_.LocalAddress -in @("0.0.0.0", "::", "127.0.0.1", "::1") 
                } | Select-Object -ExpandProperty LocalPort | Sort-Object -Unique
                
                # Extract app file name
                $appFile = "Unknown"
                if ($commandLine -match "streamlit run\s+`"?([^`"\s]+)`"?") {
                    $appFile = Split-Path $matches[1] -Leaf
                } elseif ($commandLine -match "-m streamlit run\s+`"?([^`"\s]+)`"?") {
                    $appFile = Split-Path $matches[1] -Leaf
                } elseif ($commandLine -match "streamlit-script\.py run\s+`"?([^`"\s]+)`"?") {
                    $appFile = Split-Path $matches[1] -Leaf
                } elseif ($commandLine -match "run\s+`"?([^`"\s]+\.py)`"?") {
                    $appFile = Split-Path $matches[1] -Leaf
                }
                
                $appFile = $appFile -replace '^"', '' -replace '"$', ''
                
                $streamlitProcesses += [PSCustomObject]@{
                    PID = $process.Id
                    ProcessName = $process.ProcessName
                    AppFile = $appFile
                    Ports = @($ports)
                    StartTime = $process.StartTime
                    CommandLine = $commandLine
                }
            }
        }
        catch {
            continue
        }
    }
    
    return $streamlitProcesses
}

function Show-StreamlitProcesses {
    param($processes)
    
    if ($processes.Count -eq 0) {
        Write-Host "No Streamlit applications found running." -ForegroundColor Yellow
        return
    }
    
    Write-Host "Running Streamlit Applications:" -ForegroundColor Green
    Write-Host ("=" * 60) -ForegroundColor Green
    
    foreach ($proc in $processes) {
        Write-Host "PID: $($proc.PID) | App: $($proc.AppFile) | Ports: $($proc.Ports -join ', ')" -ForegroundColor Cyan
        Write-Host "  Started: $($proc.StartTime)" -ForegroundColor Gray
        if ($proc.Ports.Count -gt 0) {
            foreach ($port in $proc.Ports) {
                Write-Host "  URL: http://localhost:$port" -ForegroundColor Magenta
            }
        }
        Write-Host ""
    }
}

function Kill-StreamlitProcess {
    param($process, [bool]$forceKill = $false)
    
    try {
        # Check if process still exists
        $existingProcess = Get-Process -Id $process.PID -ErrorAction SilentlyContinue
        if (-not $existingProcess) {
            Write-Host "✓ Process $($process.PID) no longer exists" -ForegroundColor Yellow
            return $true
        }
        
        # First attempt
        if ($forceKill) {
            Stop-Process -Id $process.PID -Force -ErrorAction Stop
            Write-Host "✓ Force killed: $($process.AppFile) (PID: $($process.PID))" -ForegroundColor Green
        } else {
            Stop-Process -Id $process.PID -ErrorAction Stop
            Write-Host "✓ Terminated: $($process.AppFile) (PID: $($process.PID))" -ForegroundColor Green
        }
        
        # Verify termination
        Start-Sleep -Milliseconds 500
        $stillExists = Get-Process -Id $process.PID -ErrorAction SilentlyContinue
        if ($stillExists) {
            Write-Host "⚠ Process still running, force killing..." -ForegroundColor Yellow
            Stop-Process -Id $process.PID -Force -ErrorAction Stop
            Start-Sleep -Milliseconds 500
            $finalCheck = Get-Process -Id $process.PID -ErrorAction SilentlyContinue
            if ($finalCheck) {
                Write-Host "✗ Failed to kill process $($process.PID)" -ForegroundColor Red
                return $false
            } else {
                Write-Host "✓ Process $($process.PID) finally terminated" -ForegroundColor Green
                return $true
            }
        }
        
        return $true
    }
    catch {
        Write-Host "✗ Failed to kill $($process.AppFile) (PID: $($process.PID)): $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# Main execution
Clear-Host
Write-Host "Streamlit Process Killer" -ForegroundColor Red
Write-Host ("=" * 30) -ForegroundColor Red

$streamlitProcesses = Get-StreamlitProcesses

if ($List) {
    Show-StreamlitProcesses -processes $streamlitProcesses
    exit
}

if ($streamlitProcesses.Count -eq 0) {
    Write-Host "No Streamlit applications found running." -ForegroundColor Yellow
    exit
}

# Handle specific ProcessId
if ($ProcessId) {
    $targetProcess = $streamlitProcesses | Where-Object { $_.PID -eq $ProcessId }
    if ($targetProcess) {
        Write-Host "Killing specific process:" -ForegroundColor Yellow
        Write-Host "PID: $($targetProcess.PID) | App: $($targetProcess.AppFile)" -ForegroundColor Cyan
        
        if (-not $Force) {
            $confirm = Read-Host "Are you sure you want to kill this process? (y/N)"
            if ($confirm -ne 'y' -and $confirm -ne 'Y') {
                Write-Host "Operation cancelled." -ForegroundColor Yellow
                exit
            }
        }
        
        $result = Kill-StreamlitProcess -process $targetProcess -forceKill $Force
        if ($result) {
            Write-Host "Process terminated successfully." -ForegroundColor Green
        } else {
            Write-Host "Failed to terminate process." -ForegroundColor Red
        }
    } else {
        Write-Host "Process ID $ProcessId not found among running Streamlit applications." -ForegroundColor Red
    }
    exit
}

# Show current processes
Show-StreamlitProcesses -processes $streamlitProcesses

# Interactive or force mode
if ($Force) {
    Write-Host "Force killing all Streamlit applications..." -ForegroundColor Red
    $killed = 0
    foreach ($proc in $streamlitProcesses) {
        if (Kill-StreamlitProcess -process $proc -forceKill $true) {
            $killed++
        }
    }
    Write-Host ""
    Write-Host "Killed $killed out of $($streamlitProcesses.Count) Streamlit applications." -ForegroundColor Green
} else {
    Write-Host ""
    $confirm = Read-Host "Kill all $($streamlitProcesses.Count) Streamlit application(s)? (y/N)"
    
    if ($confirm -eq 'y' -or $confirm -eq 'Y') {
        Write-Host "Terminating Streamlit applications..." -ForegroundColor Yellow
        $killed = 0
        foreach ($proc in $streamlitProcesses) {
            if (Kill-StreamlitProcess -process $proc -forceKill $false) {
                $killed++
            }
        }
        Write-Host ""
        Write-Host "Terminated $killed out of $($streamlitProcesses.Count) Streamlit applications." -ForegroundColor Green
    } else {
        Write-Host "Operation cancelled." -ForegroundColor Yellow
    }
}

Write-Host ""
Write-Host "Operation completed at $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
