# YouTube Ranking - Configuração Automática (Versão Auto-Detect)

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host " Configurando Automação - YouTube Ranking" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Verificar Admin
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERRO: Execute como Administrador!" -ForegroundColor Red
    pause
    exit
}

# Projeto
$projectPath = Get-Location

# Procurar Python (tentar vários locais)
Write-Host "Procurando Python..." -ForegroundColor Yellow

$pythonPaths = @(
    "$projectPath\venv\Scripts\python.exe",
    "$projectPath\.venv\Scripts\python.exe",
    "C:\Python312\python.exe",
    "C:\Python311\python.exe",
    "C:\Python310\python.exe",
    (Get-Command python -ErrorAction SilentlyContinue).Source
)

$pythonExe = $null
foreach ($path in $pythonPaths) {
    if ($path -and (Test-Path $path)) {
        $pythonExe = $path
        break
    }
}

if (-not $pythonExe) {
    Write-Host ""
    Write-Host "ERRO: Python nao encontrado!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Solucao Manual:" -ForegroundColor Yellow
    Write-Host "1. Abra o Task Scheduler (taskschd.msc)" -ForegroundColor White
    Write-Host "2. Create Basic Task" -ForegroundColor White
    Write-Host "3. Nome: YouTube Snapshots" -ForegroundColor White
    Write-Host "4. Trigger: Daily, 02:00" -ForegroundColor White
    Write-Host "5. Action: Start a program" -ForegroundColor White
    Write-Host "6. Program: python" -ForegroundColor White
    Write-Host "7. Arguments: scripts\collect_snapshots.py" -ForegroundColor White
    Write-Host "8. Start in: $projectPath" -ForegroundColor White
    Write-Host ""
    pause
    exit
}

Write-Host "Python encontrado: $pythonExe" -ForegroundColor Green
Write-Host ""

# Configurar tarefa
$taskName = "YouTube Ranking Snapshots"
$scriptPath = "scripts\collect_snapshots.py"

Write-Host "Criando tarefa..." -ForegroundColor Yellow

# Remover antiga
Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue | Unregister-ScheduledTask -Confirm:$false -ErrorAction SilentlyContinue

# Criar nova
$action = New-ScheduledTaskAction -Execute $pythonExe -Argument $scriptPath -WorkingDirectory $projectPath
$trigger = New-ScheduledTaskTrigger -Daily -At "02:00"
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries

Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Force | Out-Null

Write-Host ""
Write-Host "==========================================" -ForegroundColor Green
Write-Host " SUCESSO!" -ForegroundColor Green  
Write-Host "==========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Tarefa: $taskName" -ForegroundColor White
Write-Host "Horario: 02:00 diariamente" -ForegroundColor White
Write-Host "Python: $pythonExe" -ForegroundColor Gray
Write-Host ""

pause
