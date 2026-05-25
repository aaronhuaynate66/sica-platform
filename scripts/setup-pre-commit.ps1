# Setup de pre-commit hooks para SICA — Windows PowerShell.
#
# Instala `pre-commit` (vía pip) y configura los hooks definidos en
# `.pre-commit-config.yaml` para que corran en cada `git commit` local.
#
# Es seguro re-ejecutarlo: pre-commit install es idempotente.

$ErrorActionPreference = "Stop"

$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "✗ python no está en PATH. Instalá Python 3.11+ antes de continuar." -ForegroundColor Red
    exit 1
}

Write-Host "→ Instalando pre-commit..."
python -m pip install --upgrade --user pre-commit

Write-Host "→ Configurando hooks..."
pre-commit install

Write-Host ""
Write-Host "✓ Pre-commit hooks instalados." -ForegroundColor Green
Write-Host "  Se ejecutarán automáticamente en cada 'git commit'."
Write-Host ""
Write-Host "  Para correr sobre todo el repo ahora:"
Write-Host "    pre-commit run --all-files"
Write-Host ""
Write-Host "  Para saltar un hook puntual (último recurso):"
Write-Host "    `$env:SKIP='ruff'; git commit -m '...'"
