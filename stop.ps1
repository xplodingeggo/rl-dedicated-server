# Stop the server started by run.ps1: the server, lan_responder.py and the log windows.   .\stop.ps1
$names = Get-Process RocketLeague_Server -ErrorAction SilentlyContinue
$names | Stop-Process -Force
Get-CimInstance Win32_Process | Where-Object {
    $_.ProcessId -ne $PID -and (
    ($_.Name -eq 'python.exe' -and $_.CommandLine -match 'lan_responder') -or
    ($_.Name -eq 'powershell.exe' -and $_.CommandLine -match 'Launch\*?\.log|Launch_2\.log|FakeServer'))
} | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
"Stopped: $(@($names).Count) server process(es), the LAN responder and the log windows."
