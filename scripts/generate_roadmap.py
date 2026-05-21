#!/usr/bin/env python3
"""Genera /ROADMAP.md desde el estado actual de issues en GitHub.

Diseño:

- Determinístico: misma data de issues → mismo output. NO usa `now()`.
- Timestamp del documento se deriva del `updatedAt` máximo entre issues.
- Sin dependencias externas: stdlib + `gh` CLI invocado via subprocess.
- Idempotente: si el output coincide con el archivo en disco, no se reescribe
  (el workflow detecta este caso y no commitea).

Uso:

    python scripts/generate_roadmap.py [--repo OWNER/REPO] [--output PATH]

Salida:
    Sobreescribe /ROADMAP.md con el contenido regenerado. Log a stdout.
    Exit 0 si OK, 1 si error.

Requisitos:
    - Python 3.13+
    - `gh` CLI autenticado en el entorno (en CI: `GH_TOKEN=${{ github.token }}`).
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

DEFAULT_REPO = "aaronhuaynate66/sica-platform"
DEFAULT_OUTPUT = "ROADMAP.md"

# Tabla estática de la visión 18 meses — mirror de docs/roadmap.md
# Cambios a esta tabla deben sincronizarse con docs/roadmap.md.
RELEASES = [
    ("R0 Foundation", "0–2", "Benchmark + stack mínimo, sin UI clínica", "MedGemma 4B ≥85% factualidad, ≤5% omisiones críticas"),
    ("R1 Resumen Obstétrico (Alpha)", "2–5", "Panel standalone, sesiones de revisión", ">70% resúmenes útiles sin edición mayor"),
    ("R2 Shadow + Checklist", "5–8", "Embed en HIS, sin uso mandatorio", "≥40% uso + recall brechas ≥80% + 0 incidentes seguridad"),
    ("R3 Handoff Materno-Neonatal", "8–11", "Primer flujo crítico (asistivo)", "Completitud ≥95% + correcciones <10% + aprobación neo"),
    ("R4 Brief Preanestésico", "11–14", "Cesárea programada y urgencia", "<10% correcciones críticas + aprobación calidad"),
    ("R5 CRED + Multi-sede", "14–18", "Pediatría longitudinal + producto replicable", "Sede 2 onboarded + renovación partner"),
]

# Categorías de issues que aparecen en el roadmap.
# (label_principal, secciones_titulo)
CATEGORIES = [
    ("Regulatorio y Legal", ["regulatorio", "legal"]),
    ("GTM y Distribution", ["gtm", "distribution-engine"]),
    ("Datos y Eval", ["data", "investigacion"]),
    ("Mercado", ["mercado"]),
    ("Marca", ["marca"]),
]


@dataclass(frozen=True)
class Issue:
    number: int
    title: str
    labels: tuple[str, ...]
    state: str  # "OPEN" | "CLOSED"
    created_at: str
    updated_at: str
    closed_at: str | None
    url: str

    @property
    def label_set(self) -> set[str]:
        return set(self.labels)

    def has_label(self, name: str) -> bool:
        return name in self.label_set


def log(msg: str) -> None:
    print(f"[generate_roadmap] {msg}")


def run_gh(args: list[str]) -> str:
    """Ejecuta `gh` y devuelve stdout. Lanza RuntimeError si falla."""
    try:
        result = subprocess.run(
            ["gh", *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except FileNotFoundError as exc:
        raise RuntimeError("`gh` CLI no encontrado en PATH.") from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"`gh {' '.join(args)}` falló: {exc.stderr.strip()}") from exc
    return result.stdout


def fetch_issues(repo: str) -> list[Issue]:
    """Trae todos los issues (open + closed) del repo."""
    raw = run_gh(
        [
            "issue",
            "list",
            "--repo",
            repo,
            "--state",
            "all",
            "--limit",
            "500",
            "--json",
            "number,title,labels,state,createdAt,updatedAt,closedAt,url",
        ]
    )
    data: list[dict[str, Any]] = json.loads(raw)
    issues: list[Issue] = []
    for d in data:
        issues.append(
            Issue(
                number=int(d["number"]),
                title=str(d["title"]),
                labels=tuple(sorted(lbl["name"] for lbl in d.get("labels") or [])),
                state=str(d["state"]).upper(),
                created_at=str(d["createdAt"]),
                updated_at=str(d["updatedAt"]),
                closed_at=d.get("closedAt") or None,
                url=str(d["url"]),
            )
        )
    issues.sort(key=lambda i: i.number, reverse=True)
    return issues


def latest_bot_commit_short(bot_email: str = "sica-bot@users.noreply.github.com") -> str:
    """Devuelve el hash corto del commit más reciente del bot, o sentinel."""
    try:
        result = subprocess.run(
            ["git", "log", "--author", bot_email, "-n", "1", "--format=%h"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        out = result.stdout.strip()
        return out if out else "<sin corrida previa>"
    except FileNotFoundError:
        return "<git no disponible>"


def latest_update_iso(issues: list[Issue]) -> str:
    """Timestamp ISO del issue actualizado más recientemente.

    Si no hay issues (caso de bootstrap), devuelve "<sin issues>" como sentinel
    determinístico.
    """
    if not issues:
        return "<sin issues>"
    return max(i.updated_at for i in issues)


def fmt_labels_other(issue: Issue, exclude: set[str]) -> str:
    """Formatea labels excluyendo los listados. Devuelve "" si no quedan."""
    remaining = sorted(set(issue.labels) - exclude)
    if not remaining:
        return ""
    return " · " + " ".join(f"`{lbl}`" for lbl in remaining)


def fmt_open_line(issue: Issue, exclude: set[str]) -> str:
    """Línea Markdown con checkbox para issue abierto."""
    extras = fmt_labels_other(issue, exclude)
    return f"- [ ] **[#{issue.number}]({issue.url})** {issue.title}{extras}"


def fmt_closed_line(issue: Issue, exclude: set[str]) -> str:
    """Línea Markdown para issue cerrado."""
    extras = fmt_labels_other(issue, exclude)
    closed_at = issue.closed_at or "—"
    closed_date = closed_at.split("T")[0] if "T" in closed_at else closed_at
    return f"- [x] ~~**[#{issue.number}]({issue.url})** {issue.title}~~ · cerrado {closed_date}{extras}"


def section_r0(issues: list[Issue]) -> str:
    """Sección del release activo R0."""
    r0 = [i for i in issues if i.has_label("r0")]
    r0_open = [i for i in r0 if i.state == "OPEN"]
    r0_closed = [i for i in r0 if i.state == "CLOSED"]

    lines: list[str] = []
    lines.append("## Release activo: R0 Foundation")
    lines.append("")
    lines.append("**Período:** Mes 0–2  ")
    lines.append("**Wedge:** Benchmark + stack mínimo, sin UI clínica  ")
    lines.append("**Gate de salida:** MedGemma 4B ≥85% factualidad, ≤5% omisiones críticas")
    lines.append("")

    lines.append("### Issues abiertos en R0")
    lines.append("")
    if r0_open:
        for issue in r0_open:
            lines.append(fmt_open_line(issue, exclude={"r0", "fase-1"}))
    else:
        lines.append("_(sin issues abiertos en R0)_")
    lines.append("")

    lines.append("### Issues cerrados en R0")
    lines.append("")
    if r0_closed:
        for issue in r0_closed:
            lines.append(fmt_closed_line(issue, exclude={"r0", "fase-1"}))
    else:
        lines.append("_(sin issues cerrados en R0 todavía)_")
    lines.append("")

    lines.append("### Bloqueadores activos")
    lines.append("")
    blockers = [i for i in issues if i.has_label("bloqueante") and i.state == "OPEN"]
    if blockers:
        for issue in blockers:
            extras = fmt_labels_other(issue, exclude={"bloqueante", "fase-1"})
            lines.append(f"- 🚧 **[#{issue.number}]({issue.url})** {issue.title}{extras}")
    else:
        lines.append("_(sin bloqueadores activos)_")
    lines.append("")

    return "\n".join(lines)


def section_categories(issues: list[Issue]) -> str:
    """Sección 'Issues por categoría'."""
    lines: list[str] = []
    lines.append("## Issues por categoría")
    lines.append("")

    for title, label_set in CATEGORIES:
        relevant = [
            i
            for i in issues
            if i.state == "OPEN" and any(i.has_label(lbl) for lbl in label_set)
        ]
        lines.append(f"### {title}")
        lines.append("")
        if relevant:
            exclude = {"fase-1", *label_set}
            for issue in relevant:
                lines.append(fmt_open_line(issue, exclude=exclude))
        else:
            joined = " / ".join(f"`{lbl}`" for lbl in label_set)
            lines.append(f"_(sin issues abiertos con labels {joined})_")
        lines.append("")

    return "\n".join(lines)


def section_overview(issues: list[Issue]) -> str:
    """Tabla resumen R0–R5."""
    lines: list[str] = []
    lines.append("## Visión a 18 meses")
    lines.append("")
    lines.append("| Release | Mes | Wedge | Gate de salida |")
    lines.append("|---|---|---|---|")
    for release, month, wedge, gate in RELEASES:
        lines.append(f"| {release} | {month} | {wedge} | {gate} |")
    lines.append("")
    lines.append("Fuente detallada: [`docs/roadmap.md`](docs/roadmap.md).")
    lines.append("")
    return "\n".join(lines)


def section_status(issues: list[Issue]) -> str:
    """Sección 'Estado actual' con métricas."""
    total = len(issues)
    blockers_open = sum(
        1 for i in issues if i.has_label("bloqueante") and i.state == "OPEN"
    )
    r0 = [i for i in issues if i.has_label("r0")]
    r0_total = len(r0)
    r0_closed = sum(1 for i in r0 if i.state == "CLOSED")
    pct_r0 = round((r0_closed / r0_total) * 100) if r0_total else 0

    lines: list[str] = []
    lines.append("## Estado actual")
    lines.append("")
    lines.append("- **Release activo:** R0 Foundation (Mes 0–2)")
    lines.append(f"- **Issues totales:** {total}")
    lines.append(f"- **Bloqueantes abiertos:** {blockers_open}")
    lines.append(f"- **Progreso R0:** {r0_closed} de {r0_total} cerrados ({pct_r0}%)")
    lines.append("")
    return "\n".join(lines)


def section_next_release() -> str:
    return (
        "## Siguiente release: R1 Resumen Obstétrico (Alpha)\n"
        "\n"
        "**Período:** Mes 2–5  \n"
        "**Estado:** Pendiente. Arranca cuando R0 cierre gate.  \n"
        "**Gate de salida:** >70% resúmenes calificados útiles sin edición mayor.\n"
    )


def section_footer(last_update_iso: str, bot_commit: str) -> str:
    return (
        "## Cómo se actualiza este documento\n"
        "\n"
        "Este archivo se regenera automáticamente cada vez que:\n"
        "\n"
        "- Se abre, cierra o edita un issue\n"
        "- Se agregan o quitan labels a un issue\n"
        "- Se mergea un PR a `main`\n"
        "- Una vez al día por cron (safety net)\n"
        "- Se dispara manualmente desde Actions (`workflow_dispatch`)\n"
        "\n"
        "**No editar manualmente.** Si necesitás reflejar algo acá, hacelo cambiando "
        "los issues correspondientes en GitHub (estado, labels, título). El próximo run "
        "del workflow lo recoge.\n"
        "\n"
        "Si el workflow necesita desactivarse temporalmente, ver "
        "[ADR 0002](docs/decisions/0002-living-roadmap-system.md).\n"
        "\n"
        f"- Última generación (derivada del issue updatedAt más reciente): `{last_update_iso}`\n"
        f"- Commit que la generó: `{bot_commit}`\n"
    )


def section_header(last_update_iso: str) -> str:
    return (
        "# Roadmap SICA\n"
        "\n"
        "> Documento vivo. Se regenera automáticamente cada vez que cambian los issues en GitHub.  \n"
        f"> Última actualización (derivada de issues): `{last_update_iso}`  \n"
        "> Generado por: [`.github/workflows/sync-roadmap.yml`](.github/workflows/sync-roadmap.yml)  \n"
        "> No editar manualmente — los cambios se sobrescriben en el siguiente run.\n"
    )


def render(issues: list[Issue], bot_commit: str) -> str:
    """Construye el documento completo."""
    last_update = latest_update_iso(issues)

    parts = [
        section_header(last_update),
        "",
        section_status(issues),
        section_overview(issues),
        section_r0(issues),
        section_next_release(),
        section_categories(issues),
        section_footer(last_update, bot_commit),
    ]
    body = "\n".join(parts)
    if not body.endswith("\n"):
        body += "\n"
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera ROADMAP.md desde issues de GitHub.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="OWNER/REPO (default: %(default)s)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Ruta de salida (default: %(default)s)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe nada; exit 0 si el output coincide con el archivo en disco, 1 si difiere.",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    out_path = (repo_root / args.output).resolve()

    log(f"repo:   {args.repo}")
    log(f"output: {out_path}")

    try:
        issues = fetch_issues(args.repo)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    log(f"issues encontrados: {len(issues)} ({sum(1 for i in issues if i.state == 'OPEN')} abiertos)")

    bot_commit = latest_bot_commit_short()
    log(f"último commit del bot: {bot_commit}")

    new_content = render(issues, bot_commit)
    log(f"output renderizado: {len(new_content)} chars, {new_content.count(chr(10))} líneas")

    if out_path.exists():
        old_content = out_path.read_text(encoding="utf-8")
        if old_content == new_content:
            log("sin cambios respecto al archivo en disco — no se escribe")
            return 0

    if args.check:
        log("--check: el archivo en disco difiere del output regenerado")
        return 1

    out_path.write_text(new_content, encoding="utf-8")
    log(f"escrito: {out_path}")

    # Sanity check para CI
    if datetime.now().year < 2024:
        log("warning: año del sistema parece inválido")

    return 0


if __name__ == "__main__":
    sys.exit(main())
