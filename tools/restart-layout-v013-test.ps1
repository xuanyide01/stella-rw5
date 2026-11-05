$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$environmentRoot = Join-Path (Split-Path $projectRoot -Parent) 'stella-layout-environment'
$record = Get-Content -LiteralPath (Join-Path $environmentRoot 'controller-pid.json') | ConvertFrom-Json
if ($record.script.Replace('/','\') -ne (Join-Path $PSScriptRoot 'emulator-server.cjs')) { throw 'Wrong controller record' }
$controller = Get-CimInstance Win32_Process -Filter "ProcessId = $($record.pid)"
if ($controller) {
    if ($controller.Name -ne 'node.exe' -or $controller.CommandLine -notlike '*emulator-server.cjs*') { throw 'Controller PID was reused' }
    $emulators = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($record.pid)"
    foreach ($emulator in $emulators) {
        if ($emulator.Name -eq 'conhost.exe') { continue }
        if ($emulator.Name -ne 'emulator.exe' -or $emulator.CommandLine -notlike '*StellaLayout20261102-336x480*') { throw 'Unexpected controller child' }
        $children = Get-CimInstance Win32_Process -Filter "ParentProcessId = $($emulator.ProcessId)"
        foreach ($child in $children) {
            if ($child.Name -eq 'conhost.exe') { continue }
            if ($child.ExecutablePath -notlike '*2026-11-02\vela-sdk\emulator\*') { throw 'Unexpected emulator descendant' }
            Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
        }
        Stop-Process -Id $emulator.ProcessId -Force -ErrorAction SilentlyContinue
    }
    Stop-Process -Id $record.pid -Force -ErrorAction SilentlyContinue
}
Start-Sleep -Milliseconds 800
& (Join-Path $PSScriptRoot 'start-layout-v013-test.ps1')
