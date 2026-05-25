#!/usr/bin/env bash
# Setup de pre-commit hooks para SICA — Linux/Mac.
#
# Instala `pre-commit` (vía pip) y configura los hooks definidos en
# `.pre-commit-config.yaml` para que corran en cada `git commit` local.
#
# Es seguro re-ejecutarlo: pre-commit install es idempotente.

set -euo pipefail

if ! command -v python3 >/dev/null 2>&1; then
    echo "✗ python3 no está en PATH. Instalá Python 3.11+ antes de continuar." >&2
    exit 1
fi

echo "→ Instalando pre-commit..."
python3 -m pip install --upgrade --user pre-commit

echo "→ Configurando hooks..."
pre-commit install

echo ""
echo "✓ Pre-commit hooks instalados."
echo "  Se ejecutarán automáticamente en cada 'git commit'."
echo ""
echo "  Para correr sobre todo el repo ahora:"
echo "    pre-commit run --all-files"
echo ""
echo "  Para saltar un hook puntual (último recurso):"
echo "    SKIP=ruff git commit -m '...'"
