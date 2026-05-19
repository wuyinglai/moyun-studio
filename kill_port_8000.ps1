$connections = netstat -ano | Select-String ":8000 "
foreach ($conn in $connections) {
    $line = $conn -split '\s+'
    $p = $line[-1]
    if ($p -ne '0' -and $p -ne '') {
        try { Stop-Process -Id $p -Force -ErrorAction SilentlyContinue; Write-Output "killed $p" } catch { }
    }
}
