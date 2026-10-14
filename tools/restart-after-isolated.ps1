$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$workspaceRoot = (Resolve-Path (Join-Path $projectRoot '..')).Path
$environmentRoot = Join-Path $workspaceRoot 'stella-band8pro-environment'
$record = Get-Content -LiteralPath (Join-Path $environmentRoot 'controller-pid.json') | ConvertFrom-Json
if ($record.script -ne (Join-Path $PSScriptRoot 'emulator-server.cjs')) { throw 'Controller is not owned by this test project' }
$controllerProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.pid)"
if ($controllerProcess) {
    if ($controllerProcess.Name -ne 'node.exe' -or $controllerProcess.CommandLine -notlike '*tools/emulator-server.cjs*') { throw 'Unexpected controller identity' }
    $emulatorProcesses = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($record.pid)" | Where-Object { $_.Name -eq 'emulator.exe' }
    foreach ($emulatorProcess in $emulatorProcesses) {
        if ($emulatorProcess.CommandLine -notlike '*StellaBand8Pro-336x480*') { throw 'Emulator does not match the isolated test device' }
        Get-CimInstance Win32_Process -Filter "ParentProcessId = $($emulatorProcess.ProcessId)" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Stop-Process -Id $emulatorProcess.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $record.pid -Force -ErrorAction SilentlyContinue
}
$env:NODE_PATH = Join-Path $workspaceRoot 'starry-rw5/node_modules'
$env:STARRY_EMULATOR_HOME = $environmentRoot
$env:WATCH_SDK_HOME = Join-Path $workspaceRoot 'vela-environment/sdk'
$env:WATCH_VVD_NAME = 'StellaBand8Pro-336x480'
$env:WATCH_SERIAL_PORT = '5572'
$env:WATCH_GRPC_PORT = '8572'
$env:WATCH_DEBUG_PORT = '10072'
$env:WATCH_CONTROL_PORT = '43136'
$newController = Start-Process -FilePath 'C:\Program Files\nodejs\node.exe' -ArgumentList 'tools/emulator-server.cjs' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $environmentRoot 'controller-stdout.log') -RedirectStandardError (Join-Path $environmentRoot 'controller-stderr.log')
Write-Output $newController.Id
