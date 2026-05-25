#!/usr/bin/env bash
# Sincroniza los labels del repo con .github/labels-init.yml — Linux/Mac.
#
# Idempotente: si el label ya existe con el mismo color/descripción, no
# hace nada. Si difieren, actualiza. Nunca borra labels que no estén en
# el YAML (preserva labels históricos creados ad-hoc).
#
# Requiere: gh CLI autenticado (gh auth status).

set -euo pipefail

REPO="${REPO:-aaronhuaynate66/sica-platform}"
LABELS_FILE=".github/labels-init.yml"

if ! command -v gh >/dev/null 2>&1; then
    echo "✗ gh CLI no instalado. Instalalo desde https://cli.github.com" >&2
    exit 1
fi

if [ ! -f "$LABELS_FILE" ]; then
    echo "✗ No existe $LABELS_FILE en este directorio." >&2
    exit 1
fi

if ! command -v yq >/dev/null 2>&1; then
    echo "✗ yq no instalado. Instalalo con: brew install yq (Mac) o snap install yq (Linux)." >&2
    exit 1
fi

echo "→ Sincronizando labels de $REPO contra $LABELS_FILE..."

count=$(yq '. | length' "$LABELS_FILE")
for i in $(seq 0 $((count - 1))); do
    name=$(yq ".[$i].name" "$LABELS_FILE")
    color=$(yq ".[$i].color" "$LABELS_FILE")
    description=$(yq ".[$i].description" "$LABELS_FILE")

    if gh label list --repo "$REPO" --json name -q '.[].name' | grep -Fxq "$name"; then
        # Existe — update (idempotente).
        gh label edit "$name" --repo "$REPO" --color "$color" --description "$description" >/dev/null
        echo "  · actualizado: $name"
    else
        gh label create "$name" --repo "$REPO" --color "$color" --description "$description" >/dev/null
        echo "  + creado: $name"
    fi
done

echo ""
echo "✓ Labels sincronizados ($count total)."
