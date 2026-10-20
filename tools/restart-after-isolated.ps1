$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$workspaceRoot = (Resolve-Path (Join-Path $projectRoot '..')).Path
$environmentRoot = Join-Path $workspaceRoot 'stella-after-environment'
$record = Get-Content -LiteralPath (Join-Path $environmentRoot 'controller-pid.json') | ConvertFrom-Json
function Canonical-TestPath([string]$value) { return $value.Replace('/','\') }
if ((Canonical-TestPath $record.script) -ne (Canonical-TestPath (Join-Path $PSScriptRoot 'emulator-server.cjs'))) { throw 'Controller is not owned by this test project' }
$controllerProcess = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.pid)"
if ($controllerProcess -and ($controllerProcess.Name -ne 'node.exe' -or (Canonical-TestPath $controllerProcess.CommandLine) -notlike '*tools\emulator-server.cjs*')) {
    Write-Output 'Recorded process id has been reused; leaving the unrelated process intact'
    $controllerProcess = $null
}
if ($controllerProcess) {
    $emulatorProcesses = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($record.pid)" | Where-Object { $_.Name -eq 'emulator.exe' }
    foreach ($emulatorProcess in $emulatorProcesses) {
        if ($emulatorProcess.CommandLine -notlike '*StellaAfterRW5-432x514*') { throw 'Emulator does not match the isolated test device' }
        Get-CimInstance Win32_Process -Filter "ParentProcessId = $($emulatorProcess.ProcessId)" | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Stop-Process -Id $emulatorProcess.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $record.pid -Force -ErrorAction SilentlyContinue
}
if (Get-NetTCPConnection -LocalPort 43135 -State Listen -ErrorAction SilentlyContinue) { throw 'Test port is occupied; refusing to replace an unrelated controller' }
$env:NODE_PATH = Join-Path $workspaceRoot 'starry-rw5/node_modules'
$env:STARRY_EMULATOR_HOME = $environmentRoot
$env:WATCH_SDK_HOME = Join-Path $workspaceRoot 'vela-environment/sdk'
$env:WATCH_VVD_NAME = 'StellaAfterRW5-432x514'
$env:WATCH_SERIAL_PORT = '5570'
$env:WATCH_GRPC_PORT = '8570'
$env:WATCH_DEBUG_PORT = '10070'
$env:WATCH_CONTROL_PORT = '43135'
$newController = Start-Process -FilePath (Get-Command node -ErrorAction Stop).Source -ArgumentList 'tools/emulator-server.cjs' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $environmentRoot 'controller-stdout.log') -RedirectStandardError (Join-Path $environmentRoot 'controller-stderr.log')
Write-Output $newController.Id
