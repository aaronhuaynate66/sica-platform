#!/usr/bin/env python3
"""Genera /MASTER_PLAN.md desde el estado actual de issues, milestones, ADRs y commits.

Diseño:

- Determinístico: misma data → mismo output. NO usa `now()`.
- Timestamp del documento se deriva del `updatedAt` máximo entre issues.
- Sin dependencias externas: stdlib + `gh` CLI invocado via subprocess.
- Idempotente: si el output coincide con el archivo en disco, no se reescribe.
- 100% auto-generado: no hay secciones manuales. El archivo se reconstruye completo en cada run.

Uso:

    python scripts/generate_roadmap.py [--repo OWNER/REPO] [--output PATH]

Salida:
    Sobreescribe /MASTER_PLAN.md con el contenido regenerado. Log a stdout.
    Exit 0 si OK, 1 si error.

Requisitos:
    - Python 3.13+
    - `gh` CLI autenticado en el entorno (en CI: `GH_TOKEN=${{ github.token }}`).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

DEFAULT_REPO = "aaronhuaynate66/sica-platform"
DEFAULT_OUTPUT = "MASTER_PLAN.md"
DEFAULT_LEGACY_OUTPUT = "ROADMAP.md"  # se elimina si existe
BOT_EMAIL = "sica-bot@users.noreply.github.com"
BOT_LOGIN = "sica-bot"

# Inicio de R0 = fecha del primer commit / inicio del proyecto.
# GitHub milestones no exponen start_date, solo due_on. R0_START_DATE ancla el Gantt.
R0_START_DATE = "2026-05-20"

# Meses en español para la tabla de progreso visual (formato "MMM AAAA").
MONTH_ES = {
    1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
    7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
}

# Tabla estática de la visión 18 meses — mirror de docs/roadmap.md.
# El due_date se cruza con el milestone real en GitHub al renderizar.
RELEASES_META: list[dict[str, Any]] = [
    {
        "key": "R0",
        "title": "R0 Foundation",
        "period": "Mes 0-2",
        "wedge": "Benchmark + stack mínimo, sin UI clínica",
        "gate": "MedGemma 4B ≥85% factualidad, ≤5% omisiones críticas",
        "active": True,
    },
    {
        "key": "R1",
        "title": "R1 Resumen Obstétrico",
        "period": "Mes 2-5",
        "wedge": "Panel standalone, sesiones de revisión",
        "gate": ">70% resúmenes calificados útiles sin edición mayor",
        "active": False,
    },
    {
        "key": "R2",
        "title": "R2 Shadow Mode",
        "period": "Mes 5-8",
        "wedge": "Embed en HIS, sin uso mandatorio",
        "gate": "≥40% uso + recall brechas ≥80% + 0 incidentes seguridad",
        "active": False,
    },
    {
        "key": "R3",
        "title": "R3 Handoff Materno-Neonatal",
        "period": "Mes 8-11",
        "wedge": "Primer flujo crítico (asistivo)",
        "gate": "Completitud ≥95% + correcciones <10% + aprobación neonatología",
        "active": False,
    },
    {
        "key": "R4",
        "title": "R4 Brief Preanestésico",
        "period": "Mes 11-14",
        "wedge": "Cesárea programada y urgencia",
        "gate": "<10% correcciones críticas + aprobación calidad",
        "active": False,
    },
    {
        "key": "R5",
        "title": "R5 CRED + Multi-sede",
        "period": "Mes 14-18",
        "wedge": "Pediatría longitudinal + producto replicable",
        "gate": "Sede 2 onboarded + renovación partner",
        "active": False,
    },
]

# Categorización de issues. Orden importa: primer match gana.
# Cada regla: (titulo_seccion, labels_match, title_keywords)
CATEGORY_RULES: list[tuple[str, set[str], list[str]]] = [
    ("Regulatorio y Legal", {"regulatorio", "legal", "marca"}, []),
    ("GTM y Distribution", {"gtm", "distribution-engine"}, []),
    ("Mercado", {"mercado"}, []),
    ("Datos y Eval", {"data", "investigacion"}, ["harness", "factualidad", "métricas", "ground truth", "evaluación"]),
    ("Modelos AI", set(), ["medgemma", "routing", "modelo", "modelos"]),
    ("Seguridad", set(), ["seguridad", "phi"]),
    ("Infraestructura", set(), ["monorepo", "langfuse", "extractor", "pipeline", "setup"]),
]

# Tabla estática de infraestructura. Cambios aquí requieren PR humano.
INFRASTRUCTURE: list[tuple[str, str, str]] = [
    ("GitHub repo público", "✅ Activo", "https://github.com/aaronhuaynate66/sica-platform"),
    ("GitHub Actions CI", "✅ Activo", "ci.yml + sync-roadmap.yml"),
    ("GitHub Project (kanban)", "✅ Activo", "https://github.com/users/aaronhuaynate66/projects/2"),
    ("Milestones por release", "✅ Activo", "R0-R5 con due dates y descripciones"),
    ("Living Roadmap System", "✅ Activo", "Auto-sync MASTER_PLAN.md en cada cambio de issue"),
    ("Clinical Extractor (Python)", "✅ Local", "Probado con synthetic_case_01.pdf"),
    ("Baseline Fixture", "✅", "evals/fixtures/synthetic_case_01.expected.json"),
    ("Sentry / Observabilidad", "⬜ Pendiente", "R0 sprint"),
    ("Supabase / Postgres", "⬜ Pendiente", "R0 sprint"),
    ("Vercel deploys", "⬜ Pendiente", "R1 sprint"),
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
    milestone_title: str | None

    @property
    def label_set(self) -> set[str]:
        return set(self.labels)

    def has_label(self, name: str) -> bool:
        return name in self.label_set


@dataclass(frozen=True)
class Milestone:
    title: str
    description: str
    due_on: str | None
    state: str
    open_issues: int
    closed_issues: int


@dataclass(frozen=True)
class Commit:
    sha_short: str
    author_login: str
    author_email: str
    message_subject: str
    date: str  # ISO


@dataclass(frozen=True)
class ADR:
    number: str  # "0001"
    title: str  # "Monorepo en sica-platform con Turborepo + pnpm"
    status: str
    date: str
    filename: str


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
    """Trae todos los issues (open + closed) del repo, ordenados por número desc."""
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
            "number,title,labels,state,createdAt,updatedAt,closedAt,url,milestone",
        ]
    )
    data: list[dict[str, Any]] = json.loads(raw)
    issues: list[Issue] = []
    for d in data:
        milestone = d.get("milestone") or {}
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
                milestone_title=(milestone.get("title") if milestone else None) or None,
            )
        )
    issues.sort(key=lambda i: i.number, reverse=True)
    return issues


def fetch_milestones(repo: str) -> list[Milestone]:
    """Trae todos los milestones del repo."""
    raw = run_gh(["api", f"repos/{repo}/milestones", "--paginate", "-q", "."])
    # `gh api` paginated devuelve cada página como JSON separado. Si no hay paginación
    # da un solo JSON array. Manejamos ambos casos.
    text = raw.strip()
    if not text:
        return []
    # Intentar parsear como JSON único primero
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        # Multiple arrays concatenados
        data = []
        decoder = json.JSONDecoder()
        idx = 0
        while idx < len(text):
            chunk, end = decoder.raw_decode(text, idx)
            if isinstance(chunk, list):
                data.extend(chunk)
            else:
                data.append(chunk)
            idx = end
            while idx < len(text) and text[idx].isspace():
                idx += 1
    milestones: list[Milestone] = []
    for d in data:
        milestones.append(
            Milestone(
                title=str(d["title"]),
                description=str(d.get("description") or ""),
                due_on=d.get("due_on") or None,
                state=str(d.get("state") or "open"),
                open_issues=int(d.get("open_issues") or 0),
                closed_issues=int(d.get("closed_issues") or 0),
            )
        )
    return milestones


def fetch_recent_commits(repo: str, limit: int = 30) -> list[Commit]:
    """Trae los últimos N commits del repo (sin filtrar). Filtrado por bot ocurre después."""
    raw = run_gh(["api", f"repos/{repo}/commits", "-X", "GET", "-F", f"per_page={limit}"])
    data: list[dict[str, Any]] = json.loads(raw)
    commits: list[Commit] = []
    for d in data:
        commit = d.get("commit") or {}
        author_obj = d.get("author") or {}
        commit_author = commit.get("author") or {}
        author_login = (author_obj.get("login") if author_obj else None) or commit_author.get("name") or "unknown"
        author_email = commit_author.get("email") or ""
        subject = (commit.get("message") or "").splitlines()[0] if commit.get("message") else ""
        commits.append(
            Commit(
                sha_short=str(d["sha"])[:7],
                author_login=str(author_login),
                author_email=str(author_email),
                message_subject=subject,
                date=str(commit_author.get("date") or ""),
            )
        )
    return commits


def read_adrs(decisions_dir: Path) -> list[ADR]:
    """Lee todos los ADRs del directorio. Excluye README. Parsea Status y Date del header."""
    if not decisions_dir.exists():
        return []
    adrs: list[ADR] = []
    for path in sorted(decisions_dir.glob("*.md")):
        if path.name.lower() == "readme.md":
            continue
        text = path.read_text(encoding="utf-8")
        title_match = re.match(r"^#\s*(\d{4})\.\s+(.+?)$", text.splitlines()[0] if text.splitlines() else "")
        if not title_match:
            continue
        number = title_match.group(1)
        title = title_match.group(2).strip()
        status_match = re.search(r"\*\*Status:\*\*\s*([^\n]+)", text)
        date_match = re.search(r"\*\*Date:\*\*\s*([^\n]+)", text)
        adrs.append(
            ADR(
                number=number,
                title=title,
                status=(status_match.group(1).strip() if status_match else "Unknown"),
                date=(date_match.group(1).strip() if date_match else "—"),
                filename=path.name,
            )
        )
    return adrs


def latest_non_bot_commit_short(commits: list[Commit]) -> str:
    """Hash corto del último commit humano (no-bot)."""
    for c in commits:
        if BOT_LOGIN not in c.author_login.lower() and BOT_EMAIL.lower() not in c.author_email.lower():
            return c.sha_short
    return "<sin commits humanos>"


def latest_update_iso(issues: list[Issue]) -> str:
    """Timestamp ISO del issue actualizado más recientemente.

    Sentinel determinístico si no hay issues.
    """
    if not issues:
        return "<sin issues>"
    return max(i.updated_at for i in issues)


def progress_bar(closed: int, total: int, width: int = 40) -> str:
    """Barra ASCII de progreso. Width chars. Bloques completos vs vacíos."""
    if total <= 0:
        return "░" * width + f" 0/0 (0%)"
    pct = closed / total
    filled = int(round(pct * width))
    filled = max(0, min(width, filled))
    bar = ("█" * filled) + ("░" * (width - filled))
    return f"{bar} {closed}/{total} issues cerrados ({round(pct * 100)}%)"


def category_for(issue: Issue) -> str | None:
    """Devuelve la categoría del issue según CATEGORY_RULES, o None si no matchea."""
    title_lower = issue.title.lower()
    for section, labels, keywords in CATEGORY_RULES:
        if labels and (labels & issue.label_set):
            return section
        if keywords and any(kw in title_lower for kw in keywords):
            return section
    return None


def issue_state_glyph(issue: Issue) -> str:
    """Glifo + texto para el estado del issue."""
    if issue.state == "CLOSED":
        return "✅ Cerrado"
    return "⬜ Abierto"


def fmt_labels(labels: tuple[str, ...]) -> str:
    """Lista compacta de labels separados por coma."""
    return ", ".join(labels) if labels else "—"


def fmt_closed_date(issue: Issue) -> str:
    if issue.state != "CLOSED" or not issue.closed_at:
        return "—"
    return issue.closed_at.split("T")[0]


# ============================================================
# Helpers para timeline visual (Gantt + tabla de progreso)
# ============================================================


def iso_date_only(iso_ts: str | None) -> str | None:
    """Convierte un ISO timestamp a YYYY-MM-DD. None pasa como None."""
    if not iso_ts:
        return None
    return iso_ts.split("T")[0]


def fmt_period_es(start_ymd: str, end_ymd: str) -> str:
    """Devuelve un periodo legible en español: 'May–Jul 2026' o 'Oct 2026–Ene 2027'."""
    sy, sm, _ = start_ymd.split("-")
    ey, em, _ = end_ymd.split("-")
    smonth = MONTH_ES[int(sm)]
    emonth = MONTH_ES[int(em)]
    if sy == ey:
        return f"{smonth}–{emonth} {ey}"
    return f"{smonth} {sy}–{emonth} {ey}"


def compute_release_dates(milestones: list[Milestone]) -> dict[str, tuple[str, str]]:
    """Mapa release_title -> (start_date, end_date) en formato YYYY-MM-DD.

    Reglas:
    - R0 start = R0_START_DATE constante (GitHub no expone start_date).
    - R1..R5 start = due_on del milestone previo en RELEASES_META.
    - end = due_on del milestone propio.
    - Si un milestone no tiene due_on, se omite del mapa.
    """
    by_title = {m.title: m for m in milestones}
    dates: dict[str, tuple[str, str]] = {}
    prev_end: str | None = None
    for idx, meta in enumerate(RELEASES_META):
        ms = by_title.get(meta["title"])
        end = iso_date_only(ms.due_on) if ms else None
        if not end:
            prev_end = None  # corta la cadena de inicios derivados
            continue
        start = R0_START_DATE if idx == 0 else prev_end
        if not start:
            # Caso raro: milestone anterior sin due_on → arrancamos el día siguiente al
            # último start conocido falla; mejor saltar este release del Gantt.
            prev_end = end
            continue
        dates[meta["title"]] = (start, end)
        prev_end = end
    return dates


def release_has_open_blocker(release_key: str, issues: list[Issue]) -> bool:
    """True si hay al menos un issue OPEN con label 'bloqueante' + label del release
    (ej. 'r0') sin milestone asignado. Indica dependencia externa sin resolver.
    """
    target_label = release_key.lower()  # "R0" -> "r0"
    for issue in issues:
        if issue.state != "OPEN":
            continue
        if issue.milestone_title is not None:
            continue
        if "bloqueante" not in issue.label_set:
            continue
        if target_label in issue.label_set:
            return True
    return False


def short_progress_bar(closed: int, total: int, width: int = 10) -> str:
    """Barra ASCII compacta para la tabla de progreso visual."""
    if total <= 0:
        return "░" * width
    pct = closed / total
    filled = int(round(pct * width))
    filled = max(0, min(width, filled))
    return ("█" * filled) + ("░" * (width - filled))


def gantt_task_id(release_key: str) -> str:
    """ID Mermaid para una task del Gantt — kebab-case del key."""
    return release_key.lower()


def gantt_status_for(meta: dict[str, Any], milestone: Milestone | None, issues: list[Issue]) -> str:
    """Devuelve la cadena de status Mermaid (puede ser vacía).

    Reglas:
    - done   si milestone está closed
    - crit, active si meta.active y hay bloqueantes externos del release
    - active si meta.active sin bloqueantes
    - "" (pending) en otros casos
    """
    if milestone and milestone.state.lower() == "closed":
        return "done"
    if meta["active"]:
        if release_has_open_blocker(meta["key"], issues):
            return "crit, active"
        return "active"
    return ""


def visual_progress_state(meta: dict[str, Any], milestone: Milestone | None) -> str:
    """Estado legible para la columna 'Estado' de la tabla visual."""
    if milestone and milestone.state.lower() == "closed":
        return "✅ Completado"
    if meta["active"]:
        return "🔄 Activo"
    return "⬜ Pendiente"


# ============================================================
# Renderizado por secciones
# ============================================================


def section_visual_timeline(milestones: list[Milestone], issues: list[Issue]) -> str:
    """Diagrama Mermaid Gantt con los 6 releases.

    Cualquier release sin due_on se omite del Gantt (sin fecha no se puede dibujar).
    Si NINGÚN release tiene fechas, se omite la sección entera.
    """
    dates = compute_release_dates(milestones)
    if not dates:
        return ""

    by_title = {m.title: m for m in milestones}
    lines = [
        "## Timeline visual",
        "",
        "```mermaid",
        "gantt",
        "    title SICA Roadmap — Fase 1 (Mes 0–18)",
        "    dateFormat YYYY-MM-DD",
        "    axisFormat %b %Y",
        "",
    ]
    for meta in RELEASES_META:
        if meta["title"] not in dates:
            continue
        start, end = dates[meta["title"]]
        ms = by_title.get(meta["title"])
        status = gantt_status_for(meta, ms, issues)
        task_id = gantt_task_id(meta["key"])
        # Etiqueta de section legible
        lines.append(f"    section {meta['title']}")
        # Mermaid Gantt task syntax: "label :status, id, start, end"
        # (status omitido si vacío → "label :id, start, end")
        if status:
            lines.append(f"    {meta['title']}    :{status}, {task_id}, {start}, {end}")
        else:
            lines.append(f"    {meta['title']}    :{task_id}, {start}, {end}")
        lines.append("")
    lines.append("```")
    lines.append("")
    return "\n".join(lines)


def section_visual_progress(milestones: list[Milestone]) -> str:
    """Tabla compacta de progreso por release: período legible + estado + barra ASCII."""
    dates = compute_release_dates(milestones)
    by_title = {m.title: m for m in milestones}

    lines = [
        "**Estado por release:**",
        "",
        "| Release | Período | Estado | Progreso |",
        "|---------|---------|--------|----------|",
    ]
    any_row = False
    for meta in RELEASES_META:
        ms = by_title.get(meta["title"])
        period = ""
        if meta["title"] in dates:
            start, end = dates[meta["title"]]
            period = fmt_period_es(start, end)
        else:
            period = "—"
        state = visual_progress_state(meta, ms)
        if ms is not None:
            total = ms.open_issues + ms.closed_issues
            closed = ms.closed_issues
        else:
            total = 0
            closed = 0
        bar = short_progress_bar(closed, total)
        pct = round((closed / total) * 100) if total > 0 else 0
        lines.append(f"| {meta['title']} | {period} | {state} | {bar} {pct}% |")
        any_row = True

    if not any_row:
        return ""

    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def section_header(last_update_iso: str, head_short: str, active_release: dict[str, Any]) -> str:
    lines = [
        "# SICA — Master Plan",
        "",
        "## Estado general",
        "",
        f"Última actualización: `{last_update_iso}`  ",
        "Generado automáticamente por `.github/workflows/sync-roadmap.yml`",
        "",
        f"**Release activo:** {active_release['title']} ({active_release['period']})  ",
        f"**Hash del último commit:** `{head_short}`",
        "",
    ]
    return "\n".join(lines)


def section_overall_progress(issues: list[Issue]) -> str:
    total = len(issues)
    closed = sum(1 for i in issues if i.state == "CLOSED")
    open_count = total - closed
    blockers = sum(1 for i in issues if i.has_label("bloqueante") and i.state == "OPEN")
    # "En progreso" no es un estado nativo de GitHub Issues. Lo aproximamos como 0.
    in_progress = 0
    pending = open_count - in_progress

    lines = [
        "## Progreso general",
        "",
        "```",
        progress_bar(closed, total),
        "```",
        "",
        f"✅ Cerrados: {closed} | 🔄 En progreso: {in_progress} | "
        f"⬜ Pendientes: {pending} | 🚨 Bloqueantes: {blockers}",
        "",
        "---",
        "",
    ]
    return "\n".join(lines)


def fmt_due_date(due_on: str | None) -> str:
    if not due_on:
        return "—"
    return due_on.split("T")[0]


def section_release(
    meta: dict[str, Any],
    milestone: Milestone | None,
    release_issues: list[Issue],
) -> str:
    """Una sección por release. Tabla de issues solo si hay alguno asignado."""
    closed = sum(1 for i in release_issues if i.state == "CLOSED")
    total = len(release_issues)

    suffix = " (activo)" if meta["active"] else ""
    lines = [
        f"### {meta['title']}{suffix}",
        "",
        f"**Período:** {meta['period']}  ",
        f"**Due date:** {fmt_due_date(milestone.due_on if milestone else None)}  ",
        f"**Wedge:** {meta['wedge']}  ",
        f"**Gate de salida:** {meta['gate']}",
        "",
    ]

    if total == 0:
        if meta["active"]:
            lines.append("_(Sin issues asignados aún)_")
        else:
            lines.append("_(Sin issues asignados. Arranca cuando el release previo cierre gate.)_")
        lines.append("")
        return "\n".join(lines)

    lines.append("```")
    lines.append(progress_bar(closed, total))
    lines.append("```")
    lines.append("")
    lines.append("| # | Issue | Labels | Estado | Cerrado |")
    lines.append("|---|-------|--------|--------|---------|")
    for issue in sorted(release_issues, key=lambda i: i.number):
        lines.append(
            f"| #{issue.number} "
            f"| [{issue.title}]({issue.url}) "
            f"| {fmt_labels(issue.labels)} "
            f"| {issue_state_glyph(issue)} "
            f"| {fmt_closed_date(issue)} |"
        )
    lines.append("")
    return "\n".join(lines)


def section_releases_block(
    issues: list[Issue], milestones: list[Milestone]
) -> str:
    """Bloque con las 6 secciones de release."""
    by_title = {m.title: m for m in milestones}
    lines = ["## Progreso por Release", ""]
    for meta in RELEASES_META:
        ms = by_title.get(meta["title"])
        rel_issues = [i for i in issues if i.milestone_title == meta["title"]]
        lines.append(section_release(meta, ms, rel_issues))
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def section_blockers(issues: list[Issue]) -> str:
    """Issues sin milestone — bloqueantes externos que cruzan releases."""
    external = [i for i in issues if i.milestone_title is None]
    lines = [
        "## Bloqueantes externos (cruzan releases)",
        "",
        "Estos issues no pertenecen a un release específico. Bloquean avance "
        "de Fase 1 o requieren acciones en el mundo real.",
        "",
    ]
    if not external:
        lines.append("_(sin bloqueantes externos)_")
        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    lines.append("| # | Issue | Labels | Estado |")
    lines.append("|---|-------|--------|--------|")
    for issue in sorted(external, key=lambda i: i.number):
        lines.append(
            f"| #{issue.number} "
            f"| [{issue.title}]({issue.url}) "
            f"| {fmt_labels(issue.labels)} "
            f"| {issue_state_glyph(issue)} |"
        )
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def section_categories(issues: list[Issue]) -> str:
    """Issues agrupados por categoría. Cada issue aparece en una sola categoría."""
    buckets: dict[str, list[Issue]] = {section: [] for section, _, _ in CATEGORY_RULES}
    uncategorized: list[Issue] = []
    for issue in issues:
        cat = category_for(issue)
        if cat is None:
            uncategorized.append(issue)
        else:
            buckets[cat].append(issue)

    lines = ["## Issues por categoría", ""]
    for section, _, _ in CATEGORY_RULES:
        relevant = sorted(buckets[section], key=lambda i: i.number)
        lines.append(f"### {section}")
        lines.append("")
        if not relevant:
            lines.append("_(sin issues en esta categoría)_")
        else:
            for issue in relevant:
                glyph = "✅" if issue.state == "CLOSED" else "⬜"
                lines.append(f"- {glyph} [#{issue.number}]({issue.url}) {issue.title}")
        lines.append("")

    if uncategorized:
        lines.append("### Sin categorizar")
        lines.append("")
        for issue in sorted(uncategorized, key=lambda i: i.number):
            glyph = "✅" if issue.state == "CLOSED" else "⬜"
            lines.append(f"- {glyph} [#{issue.number}]({issue.url}) {issue.title}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def section_adrs(adrs: list[ADR]) -> str:
    """Tabla de ADRs leídos desde docs/decisions/."""
    lines = [
        "## Decisiones arquitectónicas (ADRs)",
        "",
    ]
    if not adrs:
        lines.append("_(sin ADRs registrados)_")
        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    lines.append("| # | Decisión | Estado | Fecha |")
    lines.append("|---|----------|--------|-------|")
    for adr in sorted(adrs, key=lambda a: a.number):
        link = f"docs/decisions/{adr.filename}"
        lines.append(f"| {adr.number} | [{adr.title}]({link}) | {adr.status} | {adr.date} |")
    lines.append("")
    lines.append("Auto-generado leyendo `docs/decisions/`.")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def section_commits(commits: list[Commit], limit: int = 10) -> str:
    """Últimos N commits no-bot."""
    human = [
        c for c in commits
        if BOT_LOGIN not in c.author_login.lower()
        and BOT_EMAIL.lower() not in c.author_email.lower()
    ][:limit]

    lines = [
        "## Commits recientes",
        "",
        f"Últimos {limit} commits del repo (excluyendo bot):",
        "",
    ]
    if not human:
        lines.append("_(sin commits humanos recientes)_")
        lines.append("")
        lines.append("---")
        lines.append("")
        return "\n".join(lines)

    lines.append("| Hash | Autor | Mensaje | Fecha |")
    lines.append("|------|-------|---------|-------|")
    for c in human:
        date = c.date.split("T")[0] if c.date else "—"
        # Escapar pipes en mensaje para no romper la tabla
        msg = c.message_subject.replace("|", "\\|")
        lines.append(f"| `{c.sha_short}` | {c.author_login} | {msg} | {date} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def section_infrastructure() -> str:
    lines = [
        "## Infraestructura",
        "",
        "| Item | Estado | Notas |",
        "|------|--------|-------|",
    ]
    for item, status, notes in INFRASTRUCTURE:
        lines.append(f"| {item} | {status} | {notes} |")
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


def section_footer() -> str:
    return (
        "## Cómo se mantiene este documento\n"
        "\n"
        "Auto-generado por `scripts/generate_roadmap.py` ejecutado por "
        "`.github/workflows/sync-roadmap.yml`.\n"
        "\n"
        "**Triggers de regeneración:**\n"
        "\n"
        "- Apertura, cierre, edición de un issue\n"
        "- Cambio de labels o milestone en un issue\n"
        "- Merge de un PR a `main`\n"
        "- Cron diario a las 13:00 UTC (safety net)\n"
        "- Disparo manual (`workflow_dispatch`)\n"
        "\n"
        "**No editar manualmente este archivo.** Cualquier cambio será sobrescrito "
        "en la próxima ejecución del workflow. Para cambiar el contenido visible, "
        "actualiza los issues, milestones, ADRs o commits — la fuente de verdad son ellos.\n"
        "\n"
        "---\n"
        "\n"
        "_Generado por SICA Living Roadmap System v0.2_\n"
    )


# ============================================================
# Composición
# ============================================================


def render(
    issues: list[Issue],
    milestones: list[Milestone],
    commits: list[Commit],
    adrs: list[ADR],
) -> str:
    """Construye el documento completo."""
    last_update = latest_update_iso(issues)
    head_short = latest_non_bot_commit_short(commits)
    active = next(r for r in RELEASES_META if r["active"])

    parts = [
        section_header(last_update, head_short, active),
        section_overall_progress(issues),
        section_visual_timeline(milestones, issues),
        section_visual_progress(milestones),
        section_releases_block(issues, milestones),
        section_blockers(issues),
        section_categories(issues),
        section_adrs(adrs),
        section_commits(commits),
        section_infrastructure(),
        section_footer(),
    ]
    body = "\n".join(parts)
    if not body.endswith("\n"):
        body += "\n"
    # Normalizar líneas vacías repetidas (>2 → 2)
    while "\n\n\n\n" in body:
        body = body.replace("\n\n\n\n", "\n\n\n")
    return body


def main() -> int:
    parser = argparse.ArgumentParser(description="Genera MASTER_PLAN.md desde issues, milestones, commits y ADRs.")
    parser.add_argument("--repo", default=DEFAULT_REPO, help="OWNER/REPO (default: %(default)s)")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Ruta de salida (default: %(default)s)")
    parser.add_argument(
        "--check",
        action="store_true",
        help="No escribe nada; exit 0 si el output coincide con el archivo en disco, 1 si difiere.",
    )
    parser.add_argument(
        "--keep-legacy",
        action="store_true",
        help="No eliminar el legacy ROADMAP.md (default: lo elimina si existe).",
    )
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parent.parent
    out_path = (repo_root / args.output).resolve()
    legacy_path = (repo_root / DEFAULT_LEGACY_OUTPUT).resolve()
    decisions_dir = repo_root / "docs" / "decisions"

    log(f"repo:          {args.repo}")
    log(f"output:        {out_path}")
    log(f"decisions dir: {decisions_dir}")

    try:
        issues = fetch_issues(args.repo)
        milestones = fetch_milestones(args.repo)
        commits = fetch_recent_commits(args.repo)
    except RuntimeError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    adrs = read_adrs(decisions_dir)

    log(f"issues:    {len(issues)} ({sum(1 for i in issues if i.state == 'OPEN')} abiertos)")
    log(f"milestones: {len(milestones)}")
    log(f"commits:   {len(commits)} (raw)")
    log(f"adrs:      {len(adrs)}")

    new_content = render(issues, milestones, commits, adrs)
    log(f"output renderizado: {len(new_content)} chars, {new_content.count(chr(10))} líneas")

    if out_path.exists():
        old_content = out_path.read_text(encoding="utf-8")
        if old_content == new_content:
            log("sin cambios respecto al archivo en disco — no se escribe")
            # Aún así eliminar legacy si existe
            if not args.keep_legacy and legacy_path.exists():
                legacy_path.unlink()
                log(f"legacy eliminado: {legacy_path}")
            return 0

    if args.check:
        log("--check: el archivo en disco difiere del output regenerado")
        return 1

    out_path.write_text(new_content, encoding="utf-8")
    log(f"escrito: {out_path}")

    if not args.keep_legacy and legacy_path.exists():
        legacy_path.unlink()
        log(f"legacy eliminado: {legacy_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
