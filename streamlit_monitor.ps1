# Simple Streamlit Apps Monitor
# Lists running Streamlit applications and their ports

param(
    [switch]$Detailed,
    [switch]$Help
)

if ($Help) {
    Write-Host @"
Streamlit Monitor - Lists running Streamlit applications and ports

Usage: .\streamlit_monitor.ps1 [-Detailed] [-Help]

Options:
  -Detailed    Show detailed information including command lines
  -Help        Show this help message

Examples:
  .\streamlit_monitor.ps1           # Basic listing
  .\streamlit_monitor.ps1 -Detailed # Detailed information
"@ -ForegroundColor Green
    exit
}

function Get-StreamlitApps {
    $apps = @()
    
    # Find Python processes running Streamlit
    $pythonProcesses = Get-Process -Name "python*" -ErrorAction SilentlyContinue
    
    foreach ($process in $pythonProcesses) {
        try {
            $commandLine = (Get-CimInstance Win32_Process -Filter "ProcessId = $($process.Id)").CommandLine
            
            if ($commandLine -and ($commandLine -like "*streamlit*" -or $commandLine -like "*-m streamlit*")) {
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
                
                # Clean up any remaining quotes
                $appFile = $appFile -replace '^"', '' -replace '"$', ''
                
                $apps += [PSCustomObject]@{
                    PID = $process.Id
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
    
    return $apps
}

function Show-StreamlitApps {
    param($apps, [bool]$showDetailed)
    
    if ($apps.Count -eq 0) {
        Write-Host "No Streamlit applications found." -ForegroundColor Yellow
        return
    }
    
    Write-Host "Running Streamlit Applications:" -ForegroundColor Green
    Write-Host ("=" * 50) -ForegroundColor Green
    
    foreach ($app in $apps) {
        Write-Host "App: $($app.AppFile)" -ForegroundColor Cyan
        Write-Host "PID: $($app.PID)" -ForegroundColor White
        
        if ($app.Ports.Count -gt 0) {
            Write-Host "Ports: $($app.Ports -join ', ')" -ForegroundColor Green
            foreach ($port in $app.Ports) {
                Write-Host "  URL: http://localhost:$port" -ForegroundColor Magenta
            }
        } else {
            Write-Host "Ports: None detected" -ForegroundColor Red
        }
        
        if ($showDetailed) {
            Write-Host "Started: $($app.StartTime)" -ForegroundColor Gray
            Write-Host "Command: $($app.CommandLine)" -ForegroundColor Gray
        }
        
        Write-Host ""
    }
}

function Check-CommonPorts {
    Write-Host "Checking common Streamlit ports..." -ForegroundColor Yellow
    $commonPorts = @(8501, 8502, 8503, 8504, 8505)
    $activePorts = @()
    
    foreach ($port in $commonPorts) {
        $connection = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($connection) {
            $activePorts += $port
            Write-Host "Port ${port}: ACTIVE" -ForegroundColor Green
        }
    }
    
    if ($activePorts.Count -eq 0) {
        Write-Host "No common Streamlit ports are active." -ForegroundColor Yellow
    }
}

# Main execution
Clear-Host
Write-Host "Streamlit Apps Monitor" -ForegroundColor Green
Write-Host ("=" * 30) -ForegroundColor Green

$streamlitApps = Get-StreamlitApps
Show-StreamlitApps -apps $streamlitApps -showDetailed $Detailed

Write-Host ""
Check-CommonPorts

Write-Host ""
Write-Host "Scan completed at $(Get-Date -Format 'HH:mm:ss')" -ForegroundColor Green
