param(
    [string]$SdkHome,
    [string]$EnvironmentHome,
    [string]$NodeModulesPath
)
$project = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $EnvironmentHome) { $EnvironmentHome = Join-Path $project '.emulator' }
if (-not $SdkHome) { $SdkHome = Join-Path $EnvironmentHome 'sdk' }
New-Item -ItemType Directory -Path $EnvironmentHome -Force | Out-Null
if ($NodeModulesPath) { $env:NODE_PATH = $NodeModulesPath }
$env:STARRY_EMULATOR_HOME = $EnvironmentHome
$env:WATCH_SDK_HOME = $SdkHome
$env:WATCH_VVD_NAME = 'StellaRW5-432x514'
$node = (Get-Command node).Source
$process = Start-Process -FilePath $node -ArgumentList 'tools/emulator-server.cjs' -WorkingDirectory $project -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $EnvironmentHome 'controller-stdout.log') -RedirectStandardError (Join-Path $EnvironmentHome 'controller-stderr.log')
$process.Id
