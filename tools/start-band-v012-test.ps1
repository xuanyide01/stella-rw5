$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$taskRoot = Split-Path $projectRoot -Parent
$environmentRoot = Join-Path $taskRoot 'stella-band-environment'
if (Get-NetTCPConnection -LocalPort 43152 -State Listen -ErrorAction SilentlyContinue) {
    throw 'The dedicated test port is occupied; refusing to replace another controller'
}
New-Item -ItemType Directory -Path $environmentRoot -Force | Out-Null
$env:NODE_PATH = Join-Path $taskRoot 'native-toolkit/node_modules'
$env:STARRY_EMULATOR_HOME = $environmentRoot
$env:WATCH_SDK_HOME = Join-Path $taskRoot 'vela-sdk'
$env:WATCH_VVD_NAME = 'StellaBand20261102-336x480'
$env:WATCH_SERIAL_PORT = '5582'
$env:WATCH_GRPC_PORT = '8582'
$env:WATCH_DEBUG_PORT = '10082'
$env:WATCH_CONTROL_PORT = '43152'
$node = (Get-Command node -ErrorAction Stop).Source
$controller = Start-Process -FilePath $node -ArgumentList 'tools/emulator-server.cjs' -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $environmentRoot 'controller-stdout.log') -RedirectStandardError (Join-Path $environmentRoot 'controller-stderr.log')
Write-Output $controller.Id
