# ============================================================
# Script de Backup Inteligente - Google Drive / OneDrive
# ============================================================

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Backup do Ranking Gorgonoid" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Detectar pasta de nuvem disponível
$cloudPaths = @(
    "$env:USERPROFILE\Google Drive\Meu Drive",
    "$env:USERPROFILE\Google Drive\My Drive",
    "$env:USERPROFILE\Google Drive",
    "$env:USERPROFILE\GoogleDrive",
    "G:\Meu Drive",
    "G:\My Drive",
    "$env:USERPROFILE\OneDrive"
)

$cloudPath = $null
$cloudType = ""

Write-Host "Procurando pasta de nuvem..." -ForegroundColor Yellow

foreach ($path in $cloudPaths) {
    if (Test-Path $path) {
        $cloudPath = $path
        if ($path -like "*Google*" -or $path -like "G:\*") {
            $cloudType = "Google Drive"
        } else {
            $cloudType = "OneDrive"
        }
        Write-Host "Encontrado: $cloudType" -ForegroundColor Green
        Write-Host "Local: $cloudPath" -ForegroundColor Gray
        break
    }
}

if (-not $cloudPath) {
    Write-Host ""
    Write-Host "Nenhuma pasta de nuvem encontrada!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Opções:" -ForegroundColor Yellow
    Write-Host "1. Instale o Google Drive Desktop" -ForegroundColor White
    Write-Host "   Download: https://www.google.com/drive/download/" -ForegroundColor Gray
    Write-Host ""
    Write-Host "2. Use OneDrive (já instalado no Windows)" -ForegroundColor White
    Write-Host ""
    Write-Host "3. Copie manualmente:" -ForegroundColor White
    Write-Host "   De: data\rankings.db" -ForegroundColor Gray
    Write-Host "   Para: Sua pasta de nuvem preferida" -ForegroundColor Gray
    Write-Host ""
    pause
    exit 1
}

# Criar pasta de backup
$backupDir = Join-Path $cloudPath "Backup Ranking Gorgonoid"

if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
    Write-Host "Pasta de backup criada!" -ForegroundColor Green
}

Write-Host ""

# Nome do arquivo com data
$timestamp = Get-Date -Format "yyyy-MM-dd_HHmm"
$backupFile = "$backupDir\rankings_backup_$timestamp.db"

# Copiar arquivo
Write-Host "Copiando banco de dados..." -ForegroundColor Yellow

try {
    Copy-Item "data\rankings.db" $backupFile -Force
    
    $size = (Get-Item $backupFile).Length / 1MB
    
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host " BACKUP CONCLUÍDO!" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
    Write-Host ""
    Write-Host "Destino: $cloudType" -ForegroundColor Cyan
    Write-Host "Arquivo: $backupFile" -ForegroundColor White
    Write-Host "Tamanho: $([math]::Round($size, 2)) MB" -ForegroundColor White
    Write-Host ""
    Write-Host "O arquivo será sincronizado automaticamente" -ForegroundColor Cyan
    Write-Host "com sua conta $cloudType." -ForegroundColor Cyan
    Write-Host ""
    
    # Limpar backups antigos (manter últimos 5)
    $oldBackups = Get-ChildItem $backupDir -Filter "rankings_backup_*.db" | 
                  Sort-Object LastWriteTime -Descending | 
                  Select-Object -Skip 5
    
    if ($oldBackups) {
        Write-Host "Limpando backups antigos (mantendo últimos 5)..." -ForegroundColor Yellow
        $oldBackups | Remove-Item -Force
        Write-Host "Removidos: $($oldBackups.Count) backup(s) antigo(s)" -ForegroundColor Gray
    }
    
    Write-Host ""
    Write-Host "Dica: Execute este script 1x por semana!" -ForegroundColor Cyan
    Write-Host ""
    
} catch {
    Write-Host ""
    Write-Host "ERRO ao criar backup: $_" -ForegroundColor Red
    Write-Host ""
}

pause
