"""Genera (o regenera) los archivos *.expected.meta.json de evals/fixtures/.

Para cada caso `synthetic_case_NN_xxx`:
- Calcula sha256 + size del PDF (en services/clinical-extractor/data/) y del fixture json.
- Escribe `synthetic_case_NN_xxx.expected.meta.json` con los metadatos canónicos
  según el formato establecido por synthetic_case_01.

Idempotente — re-corriendo solo actualiza hashes si los archivos cambian.

Diseño: este script existe porque escribir 8 meta files a mano es propenso a
errores (sha256 obligatorio, debe coincidir con el archivo real). Cada meta
file describe un único caso; los datos específicos por caso (case_description,
related_issues) viven en una tabla aquí.
"""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FIXTURES_DIR = REPO_ROOT / "evals" / "fixtures"
PDF_DIR = REPO_ROOT / "services" / "clinical-extractor" / "data"

# Tabla por caso. Solo se incluyen casos nuevos del Bloque A — los pre-existentes
# (01..07) mantienen sus meta files actuales sin sobreescribir.
CASES: list[dict] = [
    {
        "case_id": "synthetic_case_08_placenta_previa",
        "description": "placenta previa total con sangrado intermitente, EG 31 sem",
        "related_issues": ["#5", "#10"],
    },
    {
        "case_id": "synthetic_case_09_amenaza_parto_prematuro",
        "description": "amenaza de parto prematuro sin modificaciones cervicales, EG 28 sem",
        "related_issues": ["#5", "#10"],
    },
    {
        "case_id": "synthetic_case_10_oligohidramnios",
        "description": "oligohidramnios severo (ILA 4 cm), EG 34 sem",
        "related_issues": ["#5", "#10"],
    },
    {
        "case_id": "synthetic_case_11_hipotiroidismo",
        "description": "hipotiroidismo descompensado en gestación (Hashimoto), EG 18 sem",
        "related_issues": ["#5", "#10"],
    },
    {
        "case_id": "synthetic_case_12_itu",
        "description": "infección urinaria sintomática (E. coli) sin pielonefritis, EG 16 sem",
        "related_issues": ["#5", "#10"],
    },
    {
        "case_id": "synthetic_case_13_adolescente_vulnerable",
        "description": "gestante adolescente con vulnerabilidad psicosocial (violencia intrafamiliar), EG 14 sem",
        "related_issues": ["#5", "#10"],
    },
    {
        "case_id": "synthetic_case_14_caso_complejo",
        "description": "caso multipatología: edad materna avanzada + HTA crónica + DM2 + macrosomía, EG 36 sem",
        "related_issues": ["#5", "#10"],
    },
    {
        "case_id": "synthetic_case_15_pdf_escaneado_borroso",
        "description": "edge case técnico: mismo perfil que case_01 con escaneo borroso (ruido OCR agresivo)",
        "related_issues": ["#5", "#10"],
    },
]


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def write_meta(case_id: str, description: str, related_issues: list[str]) -> None:
    pdf_path = PDF_DIR / f"{case_id}.pdf"
    fix_path = FIXTURES_DIR / f"{case_id}.expected.json"
    meta_path = FIXTURES_DIR / f"{case_id}.expected.meta.json"

    if not pdf_path.exists():
        msg = f"PDF no existe: {pdf_path}"
        raise FileNotFoundError(msg)
    if not fix_path.exists():
        msg = f"Fixture json no existe: {fix_path}"
        raise FileNotFoundError(msg)

    meta = {
        "baseline_type": "non-clinical (synthetic data, AI-generated reference)",
        "case_description": description,
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "fixture": {
            "path": f"evals/fixtures/{case_id}.expected.json",
            "sha256": sha256_of(fix_path),
            "size_bytes": fix_path.stat().st_size,
        },
        "human_reviewer": None,
        "non_determinism_note": (
            "El fixture es una referencia hand-crafted que refleja lo que se espera "
            "que el extractor produzca dado el PDF correspondiente. El extractor real "
            "(LLM sin seed) puede diferir en ordering de evidence_spans, número exacto "
            "de spans, o confidence_score reportado. Diferencias substantivas en campos "
            "críticos (patient_age, gestational_age_weeks, lab_results, plan) requieren "
            "investigación; diferencias estilísticas (notes_summary, ordering) son benignas."
        ),
        "pdf_source": {
            "path": f"services/clinical-extractor/data/{case_id}.pdf",
            "sha256": sha256_of(pdf_path),
            "size_bytes": pdf_path.stat().st_size,
        },
        "produced_by": {
            "command": "scripts/generate_synthetic_pdfs.py + hand-crafted expected.json",
            "service": "clinical-extractor",
        },
        "related_issues": related_issues,
        "schema_version": (
            "ObstetricSummary v0 (initial — see "
            "services/clinical-extractor/src/clinical_extractor/schemas.py)"
        ),
    }

    meta_path.write_text(
        json.dumps(meta, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {meta_path.relative_to(REPO_ROOT)}")


def main() -> int:
    for case in CASES:
        write_meta(case["case_id"], case["description"], case["related_issues"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
