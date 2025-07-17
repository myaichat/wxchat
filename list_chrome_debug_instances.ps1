# PowerShell script to list Chrome debug instances
# This script identifies Chrome processes running with remote debugging enabled

Write-Host "Scanning for Chrome Debug Instances..." -ForegroundColor Cyan
Write-Host ("=" * 50)

# Function to get Chrome processes with command line arguments
function Get-ChromeDebugProcesses {
    try {
        $chromeProcesses = Get-WmiObject Win32_Process | Where-Object { 
            $_.Name -eq "chrome.exe" -and $_.CommandLine -like "*--remote-debugging-port*" 
        }
        return $chromeProcesses
    }
    catch {
        Write-Host "Error retrieving Chrome processes: $($_.Exception.Message)" -ForegroundColor Red
        return @()
    }
}

# Function to extract debug port from command line
function Get-DebugPort {
    param([string]$CommandLine)
    
    if ($CommandLine -match "--remote-debugging-port=(\d+)") {
        return $matches[1]
    }
    return $null
}

# Function to check if port is listening (simplified)
function Test-PortListening {
    param([string]$Port)
    
    try {
        $tcpClient = New-Object System.Net.Sockets.TcpClient
        $result = $tcpClient.BeginConnect("127.0.0.1", $Port, $null, $null)
        $success = $result.AsyncWaitHandle.WaitOne(1000, $false)
        $tcpClient.Close()
        return $success
    }
    catch {
        return $false
    }
}

# Function to get debug endpoint information
function Get-DebugEndpointInfo {
    param([string]$Port)
    
    try {
        $url = "http://localhost:$Port/json"
        $response = Invoke-RestMethod -Uri $url -TimeoutSec 3
        return $response
    }
    catch {
        return $null
    }
}

# Main execution
$debugProcesses = Get-ChromeDebugProcesses

if ($debugProcesses.Count -eq 0) {
    Write-Host "No Chrome debug instances found." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "To start Chrome with debugging enabled, use:" -ForegroundColor Gray
    Write-Host "   chrome.exe --remote-debugging-port=9222" -ForegroundColor Gray
    exit
}

Write-Host "Found $($debugProcesses.Count) Chrome debug instance(s):" -ForegroundColor Green
Write-Host ""

$instanceCount = 1
foreach ($process in $debugProcesses) {
    Write-Host "Debug Instance #$instanceCount" -ForegroundColor Cyan
    Write-Host "   Process ID: $($process.ProcessId)" -ForegroundColor White
    
    $debugPort = Get-DebugPort -CommandLine $process.CommandLine
    if ($debugPort) {
        Write-Host "   Debug Port: $debugPort" -ForegroundColor White
        
        # Check if port is actually listening
        $isListening = Test-PortListening -Port $debugPort
        if ($isListening) {
            Write-Host "   Status: Active (Port $debugPort is listening)" -ForegroundColor Green
            
            # Get endpoint information
            $endpointInfo = Get-DebugEndpointInfo -Port $debugPort
            if ($endpointInfo) {
                Write-Host "   Available tabs/pages: $($endpointInfo.Count)" -ForegroundColor White
                Write-Host "   Debug URL: http://localhost:$debugPort" -ForegroundColor Cyan
                
                # Show first few tabs
                $tabCount = [Math]::Min(3, $endpointInfo.Count)
                for ($i = 0; $i -lt $tabCount; $i++) {
                    $tab = $endpointInfo[$i]
                    $title = if ($tab.title.Length -gt 50) { $tab.title.Substring(0, 47) + "..." } else { $tab.title }
                    Write-Host "     Tab $($i+1): $title" -ForegroundColor Gray
                    Write-Host "            URL: $($tab.url)" -ForegroundColor DarkGray
                }
                
                if ($endpointInfo.Count -gt 3) {
                    Write-Host "     ... and $($endpointInfo.Count - 3) more tab(s)" -ForegroundColor Gray
                }
            }
        } else {
            Write-Host "   Status: Port not responding" -ForegroundColor Red
        }
    } else {
        Write-Host "   Debug Port: Not found in command line" -ForegroundColor Yellow
    }
    
    # Show command line (truncated)
    $cmdLine = $process.CommandLine
    if ($cmdLine.Length -gt 100) {
        $cmdLine = $cmdLine.Substring(0, 97) + "..."
    }
    Write-Host "   Command: $cmdLine" -ForegroundColor DarkGray
    Write-Host ""
    
    $instanceCount++
}

# Check for common debug ports
Write-Host "Checking common debug ports..." -ForegroundColor Cyan
$commonPorts = @(9222, 9223, 9224, 9225)
$foundActivePorts = @()

foreach ($port in $commonPorts) {
    if (Test-PortListening -Port $port) {
        $foundActivePorts += $port
        Write-Host "   Port $port`: Active" -ForegroundColor Green
    }
}

if ($foundActivePorts.Count -eq 0) {
    Write-Host "   No active debug ports found on common ports." -ForegroundColor Gray
}

Write-Host ""
Write-Host ("=" * 50)
Write-Host "Tips:" -ForegroundColor Yellow
Write-Host "   Access debug interface: http://localhost:[PORT]" -ForegroundColor Gray
Write-Host "   View available endpoints: http://localhost:[PORT]/json" -ForegroundColor Gray
Write-Host "   Kill debug instance: taskkill /F /PID [PROCESS_ID]" -ForegroundColor Gray
