# Quick one-liner to check Streamlit apps and ports
Get-Process python* -ErrorAction SilentlyContinue | ForEach-Object { 
    $cmd = (Get-CimInstance Win32_Process -Filter "ProcessId = $($_.Id)" -ErrorAction SilentlyContinue).CommandLine
    if ($cmd -like "*streamlit*") {
        $ports = (Get-NetTCPConnection -OwningProcess $_.Id -State Listen -ErrorAction SilentlyContinue | Where-Object {$_.LocalAddress -in @("127.0.0.1","0.0.0.0")} | Select-Object -ExpandProperty LocalPort | Sort-Object -Unique) -join ","
        $appName = if($cmd -match 'streamlit run\s+`"?([^`"\s]+)`"?'){(Split-Path $matches[1] -Leaf) -replace '^"','' -replace '"$',''}elseif($cmd -match '-m streamlit run\s+`"?([^`"\s]+)`"?'){(Split-Path $matches[1] -Leaf) -replace '^"','' -replace '"$',''}elseif($cmd -match 'streamlit-script\.py run\s+`"?([^`"\s]+)`"?'){(Split-Path $matches[1] -Leaf) -replace '^"','' -replace '"$',''}elseif($cmd -match 'run\s+`"?([^`"\s]+\.py)`"?'){(Split-Path $matches[1] -Leaf) -replace '^"','' -replace '"$',''}else{'Unknown'}
        Write-Host "PID: $($_.Id) | Ports: $ports | App: $appName" -ForegroundColor Green
    }
}
