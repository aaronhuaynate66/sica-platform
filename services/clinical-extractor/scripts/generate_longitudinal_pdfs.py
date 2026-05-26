"""Generador de los 4 PDFs longitudinales — caso Lucía Mendoza Quispe.

A diferencia de ``generate_synthetic_pdfs.py`` (15 casos puntuales no
relacionados entre sí), este script produce **4 PDFs del mismo embarazo**
en distintas semanas de gestación. Diseñado para evaluar continuidad
clínica del extractor entre controles:

    sem 16  →  primer control completo, antecedentes + análisis 1er trim
    sem 24  →  PTOG positiva, diagnóstico de DIABETES GESTACIONAL
    sem 32  →  deterioro metabólico, inicio de INSULINA
    sem 38  →  macrosomía confirmada, decisión de CESÁREA electiva

Paciente sintética: Lucía Mendoza Quispe, DNI 47812936, HC HCL-2024-08847.
NO ES PACIENTE REAL — datos completamente inventados. Header explícito
en cada PDF.

Helpers (``_styles``, ``_kv_table``, ``_labs_table``, ``_build_doc``,
``_header_block``, ``_footer_block``) se importan del script existente
para mantener look-and-feel uniforme con synthetic_case_01-15.

Uso:

    python services/clinical-extractor/scripts/generate_longitudinal_pdfs.py

Idempotente: regenera los 4 PDFs desde cero.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Helpers reused from the sibling script
sys.path.insert(0, str(Path(__file__).resolve().parent))
from generate_synthetic_pdfs import (
    _build_doc,
    _footer_block,
    _header_block,
    _kv_table,
    _labs_table,
    _styles,
)
from reportlab.platypus import Paragraph, Spacer

OUT_DIR = Path(__file__).resolve().parent.parent / "data"


# =========================================================================
# Caso longitudinal — sem 16 (primer control completo)
# =========================================================================
def build_lucia_sem16(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA — CONTROL PRENATAL", s["title"]),
        Paragraph(
            "Centro Materno Infantil Tahuantinsuyo Bajo (sintético) — Consultorio Obstetricia",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "Lucía Mendoza Quispe (SINTÉTICA - NO REAL)"),
                ("DNI:", "47812936"),
                ("HC:", "HCL-2024-08847"),
                ("Fecha nacimiento:", "15/03/1996"),
                ("Edad:", "28 años"),
                ("Estado civil:", "Conviviente"),
                ("Ocupación:", "Comerciante"),
                ("Domicilio:", "Av. Los Pinos 234, San Juan de Lurigancho, Lima"),
                ("Fecha consulta:", "15/04/2024"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G2 P1. Parto vaginal previo en 2019, RN de 3,200 g sin "
            "complicaciones. Lactancia materna 6 meses. Régimen catamenial previo regular.",
            s["p"],
        ),
        Paragraph("ANTECEDENTES PERSONALES Y FAMILIARES", s["h1"]),
        Paragraph(
            "Personales: niega diabetes, hipertensión, asma. Sin antecedentes quirúrgicos. "
            "Familiares: madre con DIABETES MELLITUS TIPO 2 diagnosticada a los 50 años "
            "(antecedente relevante para riesgo de diabetes gestacional).",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUR:", "27/12/2023"),
                ("FPP:", "03/10/2024"),
                ("EG actual (por FUR):", "16 semanas + 2 días"),
                ("Embarazo:", "Único"),
                ("Controles prenatales:", "2 al momento (incluye éste)"),
            ]
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        _kv_table(
            [
                ("Peso actual:", "67.5 kg (ganancia 3.5 kg)"),
                ("Peso pre-gestacional:", "64.0 kg"),
                ("Talla:", "1.58 m"),
                ("IMC pre-gestacional:", "25.6 (sobrepeso leve)"),
                ("PA:", "110/70 mmHg"),
                ("FC:", "78 lpm"),
                ("AU:", "14 cm"),
                ("FCF (Doppler):", "152 lpm"),
                ("Edemas:", "Ausentes"),
            ]
        ),
        Paragraph("LABORATORIOS DEL PRIMER TRIMESTRE (sem 12)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "11.8", "g/dL", "Dentro de rango"),
                ("Hematocrito", "35.2", "%", "Normal"),
                ("Glicemia en ayunas", "92", "mg/dL", "Límite alto-normal"),
                ("Grupo y factor Rh", "O Rh+", "—", "—"),
                ("VIH (ELISA)", "No reactivo", "—", "Negativo"),
                ("VDRL", "No reactivo", "—", "Negativa"),
                ("HBsAg", "No reactivo", "—", "Negativo"),
                ("Urocultivo", "Negativo", "—", "Sin crecimiento bacteriano"),
            ]
        ),
        Paragraph("ECOGRAFÍA DEL PRIMER TRIMESTRE (sem 11+4)", s["h1"]),
        Paragraph(
            "Feto único intrauterino. CCN compatible con edad gestacional 11 semanas 4 días. "
            "Latidos fetales presentes y regulares. Translucencia nucal dentro de rango. "
            "No se evidencian malformaciones estructurales en este momento del desarrollo.",
            s["p"],
        ),
        Paragraph("DIAGNÓSTICO", s["h1"]),
        Paragraph(
            "1. Embarazo de 16 semanas + 2 días por FUR. "
            "2. Sobrepeso pre-gestacional (IMC 25.6). "
            "3. Antecedente familiar de DM2 — riesgo aumentado de diabetes gestacional.",
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Continuar ácido fólico 5 mg/día y sulfato ferroso 60 mg/día. "
            "2. Educación nutricional básica orientada a control de peso. "
            "3. **PTOG con 75 g en semana 24** por factores de riesgo (sobrepeso + AF de DM2). "
            "4. Próximo control en 4 semanas (semana 20). "
            "5. Signos de alarma instruidos: sangrado, dolor abdominal severo, ausencia "
            "de movimientos fetales, edema súbito o cefalea persistente.",
            s["p"],
        ),
        Spacer(1, 12),
        Paragraph(
            "Médico tratante: Dr. Juan Carlos Vásquez Torres — CMP 45821",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso longitudinal — sem 24 (PTOG positiva, dx DIABETES GESTACIONAL)
# =========================================================================
def build_lucia_sem24(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA — CONTROL PRENATAL", s["title"]),
        Paragraph(
            "Centro Materno Infantil Tahuantinsuyo Bajo (sintético) — Consultorio Obstetricia",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "Lucía Mendoza Quispe (SINTÉTICA - NO REAL)"),
                ("DNI:", "47812936"),
                ("HC:", "HCL-2024-08847"),
                ("Edad:", "28 años"),
                ("Fecha consulta:", "10/06/2024"),
            ]
        ),
        Paragraph("ANTECEDENTES (referidos del control previo de sem 16)", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G2 P1 (parto vaginal 2019, RN 3,200 g sin complicaciones). "
            "Antecedente familiar materno de DM2 (madre dx a los 50 años). "
            "Sobrepeso pre-gestacional (IMC 25.6). Control previo realizado el 15/04/2024 "
            "por Dr. Vásquez con plan de PTOG en sem 24.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUR:", "27/12/2023"),
                ("FPP:", "03/10/2024"),
                ("EG actual:", "24 semanas + 1 día"),
                ("Controles prenatales:", "4 al momento"),
                ("Movimientos fetales:", "Percibidos por la madre, normales"),
            ]
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        _kv_table(
            [
                ("Peso actual:", "71.2 kg (ganancia total 7.2 kg)"),
                ("PA:", "118/74 mmHg"),
                ("FC:", "82 lpm"),
                ("AU:", "24 cm (concordante con EG)"),
                ("FCF:", "148 lpm"),
                ("Edemas:", "Ausentes"),
            ]
        ),
        Paragraph("LABORATORIOS DE ESTE CONTROL", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "11.2", "g/dL", "Leve descenso esperado"),
                ("Urocultivo", "Negativo", "—", "Sin crecimiento"),
                ("PTOG 75g — basal", "98", "mg/dL", "Normal (<92 normal, 92-125 alterado)"),
                ("PTOG 75g — 1 h", "178", "mg/dL", "Casi al límite (criterio >180)"),
                ("PTOG 75g — 2 h", "162", "mg/dL", "ALTERADO (criterio >153)"),
            ]
        ),
        Paragraph("ECOGRAFÍA MORFOLÓGICA (sem 22)", s["h1"]),
        Paragraph(
            "Feto único en presentación cefálica. Peso fetal estimado 580 g (percentil 50). "
            "Anatomía sistemática: SIN malformaciones estructurales evidentes. "
            "Placenta corporal anterior, grado 0. "
            "Líquido amniótico: ILA 14 cm (normal). "
            "Doppler arteria uterina: índice de pulsatilidad dentro de percentiles normales.",
            s["p"],
        ),
        Paragraph("DIAGNÓSTICO", s["h1"]),
        Paragraph(
            "1. Embarazo de 24 semanas. "
            "2. **DIABETES GESTACIONAL** (criterio IADPSG/ADA cumplido: valor 2 h post-carga "
            "162 mg/dL > 153 mg/dL). "
            "3. Sobrepeso pre-gestacional persistente.",
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. **Interconsulta a Endocrinología** para evaluación y conducta. "
            "2. **Interconsulta a Nutrición** para plan alimentario individualizado. "
            "3. Inicio de **dieta para diabetes gestacional**: 1800 kcal/día fraccionadas "
            "en 6 tomas (3 comidas + 3 colaciones), distribución 45% carbohidratos / 25% "
            "proteínas / 30% grasas. "
            "4. **Automonitoreo de glicemias capilares**: 4 controles diarios (basal + "
            "1 hora post-prandial x 3 comidas principales). "
            "5. Educación sobre signos de alarma de DG: hipoglucemia, hiperglucemia, "
            "cetonuria. Manejo emergencia diabética. "
            "6. Continuar sulfato ferroso 60 mg/día + ácido fólico 5 mg/día. "
            "7. Próximo control en 2 semanas (sem 26) para evaluar respuesta a dieta.",
            s["p"],
        ),
        Spacer(1, 12),
        Paragraph(
            "Médico tratante: Dr. Juan Carlos Vásquez Torres — CMP 45821",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso longitudinal — sem 32 (deterioro, INICIO INSULINA)
# =========================================================================
def build_lucia_sem32(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA — CONTROL PRENATAL", s["title"]),
        Paragraph(
            "Centro Materno Infantil Tahuantinsuyo Bajo (sintético) — Consultorio Obstetricia",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "Lucía Mendoza Quispe (SINTÉTICA - NO REAL)"),
                ("DNI:", "47812936"),
                ("HC:", "HCL-2024-08847"),
                ("Edad:", "28 años"),
                ("Fecha consulta:", "19/08/2024"),
            ]
        ),
        Paragraph("ANTECEDENTES (resumen de controles previos)", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G2 P1. Antecedente familiar DM2 (madre). "
            "Sobrepeso pre-gestacional (IMC 25.6). "
            "**DIABETES GESTACIONAL** diagnosticada en sem 24 (10/06/2024) por PTOG alterada. "
            "En dieta para diabéticas desde sem 24 con controles cada 2 semanas. "
            "Refiere que las glicemias capilares han aumentado en las últimas 2 semanas "
            "a pesar de adherencia estricta a la dieta.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUR:", "27/12/2023"),
                ("FPP:", "03/10/2024"),
                ("EG actual:", "32 semanas + 4 días"),
                ("Controles prenatales:", "8 al momento"),
                ("Movimientos fetales:", "Presentes, percibidos normalmente"),
            ]
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        _kv_table(
            [
                ("Peso actual:", "76.8 kg (ganancia total 12.8 kg)"),
                ("PA:", "122/78 mmHg"),
                ("FC:", "86 lpm"),
                ("AU:", "33 cm (1 cm por encima de EG)"),
                ("FCF:", "144 lpm"),
                ("Edemas:", "Pretibiales +/4 (leves)"),
            ]
        ),
        Paragraph("AUTOMONITOREO DE GLICEMIAS (últimas 2 semanas)", s["h1"]),
        _labs_table(
            [
                ("Glicemia basal — promedio", "102", "mg/dL", "ALTERADO (objetivo <95)"),
                (
                    "Glicemia 1 h post-prandial — promedio",
                    "145",
                    "mg/dL",
                    "ALTERADO (objetivo <140)",
                ),
                ("HbA1c", "6.2", "%", "Alto para embarazo (objetivo <6.0)"),
            ]
        ),
        Paragraph("ECOGRAFÍA DE CONTROL (sem 32)", s["h1"]),
        Paragraph(
            "Feto único vivo en presentación cefálica. "
            "Peso fetal estimado: 2,100 g (percentil 85 — TENDENCIA A MACROSOMÍA). "
            "Anatomía conservada. "
            "Líquido amniótico: ILA 22 cm (POLIHIDRAMNIOS leve — asociado a DG). "
            "Doppler umbilical normal. "
            "Placenta corporal anterior, grado II.",
            s["p"],
        ),
        Paragraph("OTROS LABORATORIOS", s["h1"]),
        _labs_table(
            [
                ("Urocultivo", "Negativo", "—", "Sin crecimiento"),
                ("Proteinuria cualitativa", "Negativo", "—", "Sin proteinuria"),
            ]
        ),
        Paragraph("DIAGNÓSTICO", s["h1"]),
        Paragraph(
            "1. Embarazo de 32 semanas + 4 días. "
            "2. **Diabetes gestacional MAL CONTROLADA con dieta** (HbA1c 6.2%, glicemias "
            "ayunas promedio 102 mg/dL, post-prandiales 145 mg/dL). "
            "3. **Macrosomía fetal incipiente** (PFE p85). "
            "4. **Polihidramnios leve** (ILA 22 cm).",
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. **INICIO DE INSULINA NPH** 10 UI subcutáneas en la noche (antes de cenar). "
            "2. Reforzar dieta para diabéticas con énfasis en fraccionamiento adecuado. "
            "3. Aumentar **automonitoreo a 6 controles diarios** (basal + pre-prandial + "
            "1 hora post-prandial x 3 comidas). "
            "4. Reevaluación en **1 semana** para titulación de dosis de insulina según "
            "respuesta glicémica. "
            "5. **Ecografía de control en sem 36** para reevaluación de peso fetal. "
            "6. **Conteo diario de movimientos fetales** (al menos 10 mov/2 h en periodos "
            "de actividad). "
            "7. Refuerzo de signos de alarma: hipoglucemia severa, ausencia de movimientos "
            "fetales, sangrado, pérdida de líquido amniótico, contracciones regulares.",
            s["p"],
        ),
        Spacer(1, 12),
        Paragraph(
            "Médico tratante: Dr. Juan Carlos Vásquez Torres — CMP 45821",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso longitudinal — sem 38 (decisión de VÍA DE PARTO — cesárea)
# =========================================================================
def build_lucia_sem38(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA — CONTROL PRENATAL", s["title"]),
        Paragraph(
            "Centro Materno Infantil Tahuantinsuyo Bajo (sintético) — Consultorio Obstetricia",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "Lucía Mendoza Quispe (SINTÉTICA - NO REAL)"),
                ("DNI:", "47812936"),
                ("HC:", "HCL-2024-08847"),
                ("Edad:", "28 años"),
                ("Fecha consulta:", "14/10/2024"),
            ]
        ),
        Paragraph("ANTECEDENTES (resumen completo del embarazo)", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G2 P1 (parto vaginal previo 2019, RN 3,200 g sin "
            "complicaciones). Antecedente familiar DM2 (madre). "
            "Sobrepeso pre-gestacional (IMC 25.6). "
            "**Diabetes gestacional diagnosticada en sem 24** por PTOG alterada. "
            "**Inicio de dieta diabética** desde sem 24. "
            "**Inicio de insulina NPH** en sem 32 (10 UI nocturnas) por mal control con dieta. "
            "**Titulación progresiva**: actualmente 18 UI nocturnas + 8 UI matutinas. "
            "Promedio de glicemias últimas 2 semanas: ayunas 88 mg/dL, post-prandiales 128 "
            "mg/dL (CONTROLADAS).",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUR:", "27/12/2023"),
                ("FPP:", "03/10/2024"),
                ("EG actual:", "38 semanas + 2 días"),
                ("Controles prenatales:", "12 al momento"),
                ("Movimientos fetales:", "Presentes, ≥10/2 h"),
            ]
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        _kv_table(
            [
                ("Peso actual:", "82.4 kg (ganancia total 18.4 kg)"),
                ("PA:", "124/76 mmHg"),
                ("FC:", "84 lpm"),
                ("AU:", "39 cm"),
                ("FCF:", "142 lpm"),
                ("Edemas:", "++/4 maleolares (esperables, no signo de PE)"),
                ("Reflejos osteotendinosos:", "Normales"),
                (
                    "Tacto vaginal (con consentimiento):",
                    "Cuello posterior, dehiscente, 50% borrado",
                ),
                ("Presentación:", "Cefálica encajada en plano -2"),
            ]
        ),
        Paragraph("ECOGRAFÍA RECIENTE (sem 37)", s["h1"]),
        Paragraph(
            "Feto único vivo en presentación cefálica. "
            "Peso fetal estimado: **3,850 g (percentil 90 — MACROSOMÍA CONFIRMADA)**. "
            "Anatomía conservada. "
            "Líquido amniótico: ILA 18 cm (normal alto). "
            "Doppler umbilical, arteria cerebral media y ducto venoso: NORMALES. "
            "Placenta grado III, sin signos de insuficiencia placentaria.",
            s["p"],
        ),
        Paragraph("LABORATORIOS RECIENTES", s["h1"]),
        _labs_table(
            [
                ("HbA1c", "5.8", "%", "Controlada"),
                ("Hemoglobina", "10.9", "g/dL", "Leve anemia esperable"),
                ("Urocultivo", "Negativo", "—", "Sin crecimiento"),
                ("Proteinuria cualitativa", "Negativo", "—", "Sin proteinuria"),
                ("Test no estresante", "Reactivo", "—", "Bienestar fetal conservado"),
            ]
        ),
        Paragraph("DIAGNÓSTICO", s["h1"]),
        Paragraph(
            "1. Embarazo de 38 semanas + 2 días. "
            "2. **Diabetes gestacional CONTROLADA con insulina** (HbA1c 5.8%). "
            "3. Feto único vivo en presentación cefálica. "
            "4. **Macrosomía fetal** (PFE 3,850 g, percentil 90).",
            s["p"],
        ),
        Paragraph("PLAN — DECISIÓN DE VÍA DE PARTO", s["h1"]),
        Paragraph(
            "Análisis: macrosomía con PFE >4,000 g esperado al término en contexto de "
            "DG, sumado al riesgo aumentado de distocia de hombros. Antecedente de parto "
            "vaginal previo SIN complicaciones (RN 3,200 g) NO es protector ante el peso "
            "fetal proyectado.",
            s["p"],
        ),
        Paragraph(
            "**DECISIÓN: CESÁREA ELECTIVA programada para semana 39** (próxima semana). "
            "Justificación: riesgo aumentado de distocia de hombros con PFE >4,000 g + DG. "
            "Referir a hospital de mayor complejidad (II-2 o III-1) por riesgo metabólico "
            "neonatal asociado a hijo de madre con DG.",
            s["p"],
        ),
        Paragraph("INDICACIONES", s["h1"]),
        Paragraph(
            "1. Continuar dieta diabética + insulina hasta el día de la cirugía. "
            "Omitir dosis matutina el día de la cesárea. "
            "2. **Consentimiento informado** firmado para cesárea (riesgos y beneficios "
            "explicados). "
            "3. **Conteo diario de movimientos fetales** hasta la cesárea. "
            "4. **Test no estresante semanal** mientras se espera. "
            "5. Signos de alarma para acudir a emergencia obstétrica: sangrado, "
            "contracciones regulares antes de la fecha programada, pérdida de líquido "
            "amniótico, disminución de movimientos fetales, cefalea/edema súbito. "
            "6. Cita en hospital referido para evaluación pre-quirúrgica (anestesiología, "
            "valoración cardiovascular).",
            s["p"],
        ),
        Spacer(1, 12),
        Paragraph(
            "Médico tratante: Dr. Juan Carlos Vásquez Torres — CMP 45821",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Main
# =========================================================================
def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    cases = [
        ("longitudinal_lucia_sem16.pdf", build_lucia_sem16),
        ("longitudinal_lucia_sem24.pdf", build_lucia_sem24),
        ("longitudinal_lucia_sem32.pdf", build_lucia_sem32),
        ("longitudinal_lucia_sem38.pdf", build_lucia_sem38),
    ]
    for filename, builder in cases:
        out = OUT_DIR / filename
        builder(out)
        size_kb = out.stat().st_size / 1024
        print(f"wrote {out.relative_to(OUT_DIR.parent.parent.parent)} ({size_kb:.1f} KB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
