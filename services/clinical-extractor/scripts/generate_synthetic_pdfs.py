"""Generador de PDFs sintéticos para el harness de evals.

Cada PDF representa un caso obstétrico distinto, diseñado para ejercitar
distintos modos del extractor:

- case_02: preeclampsia con proteinuria + plaquetopenia
- case_03: embarazo gemelar bicorial biamniótico
- case_04: ruptura prematura de membranas (RPM)
- case_05: diabetes gestacional
- case_06: anemia severa ferropénica
- case_07: control normal — versión con ruido tipo OCR/manuscrito

Todos los PDFs llevan en pagina 1 el encabezado:

    DATOS SINTÉTICOS - SOLO PARA PRUEBAS - NO ES PACIENTE REAL

Reglas:
- NO usar nombres reales, NO PHI.
- Datos médicamente coherentes consigo mismos (no contradictorios).
- PDFs pequeños (objetivo: 1-3 KB cada uno, máximo 2 páginas).

Uso:

    python services/clinical-extractor/scripts/generate_synthetic_pdfs.py

Idempotente: regenera todos los PDFs desde cero. Determinista en contenido,
no determinista en bytes exactos (reportlab incluye timestamps internos).
"""
from __future__ import annotations

import random
import sys
from pathlib import Path

from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors

OUT_DIR = Path(__file__).resolve().parent.parent / "data"

HEADER = (
    "DATOS SINTÉTICOS - SOLO PARA PRUEBAS - NO ES PACIENTE REAL"
)
DISCLAIMER = (
    "Este documento fue generado automáticamente para el desarrollo del "
    "clinical-extractor de SICA. No contiene PHI ni representa una paciente "
    "real. Cualquier semejanza con un caso clínico real es coincidencia."
)
FOOTER = (
    "Documento generado para fines de prueba del clinical-extractor de SICA. "
    "Sintético. No representa una paciente real."
)


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontSize=13,
            leading=15,
            spaceAfter=6,
            alignment=TA_LEFT,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading2"],
            fontSize=11,
            leading=13,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "p": ParagraphStyle(
            "p",
            parent=base["BodyText"],
            fontSize=9,
            leading=11,
        ),
        "header": ParagraphStyle(
            "header",
            parent=base["BodyText"],
            fontSize=9,
            leading=11,
            textColor=colors.black,
            backColor=colors.lightgrey,
            borderPadding=4,
            spaceAfter=4,
        ),
        "small": ParagraphStyle(
            "small",
            parent=base["BodyText"],
            fontSize=8,
            leading=10,
            textColor=colors.grey,
        ),
    }


def _kv_table(rows: list[tuple[str, str]]) -> Table:
    """Two-column key/value table replicating the case_01 layout."""
    data = [[k, v] for k, v in rows]
    t = Table(data, colWidths=[1.7 * inch, 4.3 * inch])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.black),
                ("BACKGROUND", (0, 0), (0, -1), colors.whitesmoke),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.lightgrey),
            ]
        )
    )
    return t


def _labs_table(rows: list[tuple[str, str, str, str]]) -> Table:
    header = ["Analito", "Resultado", "Unidad", "Observación"]
    data = [header, *[list(r) for r in rows]]
    t = Table(data, colWidths=[1.7 * inch, 1.1 * inch, 1.0 * inch, 2.2 * inch])
    t.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return t


def _build_doc(path: Path, story: list) -> None:
    doc = SimpleDocTemplate(
        str(path),
        pagesize=LETTER,
        leftMargin=0.7 * inch,
        rightMargin=0.7 * inch,
        topMargin=0.6 * inch,
        bottomMargin=0.6 * inch,
        title="Sintético - SICA clinical-extractor",
        author="SICA Platform (synthetic)",
    )
    doc.build(story)


def _header_block(s: dict[str, ParagraphStyle]) -> list:
    return [
        Paragraph(f"■ {HEADER} ■", s["header"]),
        Paragraph(DISCLAIMER, s["small"]),
        Spacer(1, 6),
    ]


def _footer_block(s: dict[str, ParagraphStyle]) -> list:
    return [
        Spacer(1, 8),
        Paragraph(FOOTER, s["small"]),
    ]


# =========================================================================
# Caso 02 — preeclampsia
# =========================================================================
def build_case_02(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Hospitalización Obstétrica",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", "35 años"),
                ("Estado civil:", "Casada"),
                ("Ocupación:", "Docente"),
                ("Fecha de elaboración:", "10/05/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G3 P2 (2 partos vaginales previos, 2018 y 2021, sin complicaciones).",
            s["p"],
        ),
        Paragraph(
            "Niega antecedentes de hipertensión crónica, diabetes ni nefropatía. "
            "Sin antecedentes familiares de preeclampsia.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "01/10/2025"),
                ("FPP:", "08/07/2026"),
                ("EG actual (por FUM):", "32 semanas"),
                ("Controles prenatales:", "7 al momento"),
                ("Motivo de ingreso:", "Hipertensión gestacional severa con proteinuria"),
            ]
        ),
        Paragraph(
            "Paciente refiere cefalea persistente y edema progresivo en miembros inferiores en últimas 48 h. "
            "Niega epigastralgia, visión borrosa o tinnitus. Movimientos fetales presentes y normales.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        Paragraph(
            "PA 158/102 mmHg (confirmada en dos tomas separadas por 4 h). FC 88 lpm. T° 36.6°C. "
            "Peso 78.2 kg. Edema MMII (++/-) hasta tercio medio de pierna. "
            "Reflejos osteotendinosos normales. AU 30 cm. LCF 144 lpm.",
            s["p"],
        ),
        Paragraph("LABORATORIOS (10/05/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "11.8", "g/dL", "Dentro de rango"),
                ("Plaquetas", "95000", "/mm³", "Plaquetopenia"),
                ("Creatinina", "0.9", "mg/dL", "Normal"),
                ("AST (TGO)", "38", "U/L", "Discreto incremento"),
                ("ALT (TGP)", "42", "U/L", "Discreto incremento"),
                ("LDH", "320", "U/L", "Normal-alto"),
                ("Proteinuria tira", "2+", "—", "Cualitativa positiva"),
                ("Proteinuria 24 h", "1.8", "g/24 h", "Significativa"),
            ]
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Hospitalización en sala obstétrica de alto riesgo. "
            "2. Inicio de sulfato de magnesio según protocolo (dosis de carga 4 g EV en 20 min, "
            "mantenimiento 1 g/h). "
            "3. Maduración pulmonar fetal con betametasona 12 mg IM c/24 h x 2 dosis. "
            "4. Antihipertensivos según meta de PA <150/100. "
            "5. Monitoreo materno (PA c/15 min, diuresis horaria) y fetal (NST diario). "
            "6. Reevaluación obstétrica para definir momento y vía de parto.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 03 — gemelar bicorial biamniótico
# =========================================================================
def build_case_03(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Consultorio de Alto Riesgo Obstétrico",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", "28 años"),
                ("Estado civil:", "Conviviente"),
                ("Ocupación:", "Asistente contable"),
                ("Fecha de elaboración:", "20/03/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G2 P1 (1 parto vaginal previo, 2023, embarazo único, sin complicaciones).",
            s["p"],
        ),
        Paragraph(
            "Niega antecedentes familiares de gemelaridad. "
            "Concepción espontánea, sin tratamientos de fertilidad.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "08/10/2025"),
                ("FPP:", "15/07/2026"),
                ("EG actual (por FUM):", "24 semanas"),
                ("Tipo de embarazo:", "Gemelar bicorial biamniótico"),
                ("Controles prenatales:", "4 al momento"),
            ]
        ),
        Paragraph(
            "Eco a las 12 semanas confirmó corionicidad: dos sacos, dos placentas, signo lambda positivo. "
            "Última eco (18 semanas) con crecimiento concordante entre ambos fetos.",
            s["p"],
        ),
        Paragraph("ECOGRAFÍA OBSTÉTRICA (18 SEMANAS)", s["h1"]),
        Paragraph(
            "Feto A: vivo, presentación cefálica, biometría acorde a EG, peso fetal estimado 235 g. "
            "Feto B: vivo, presentación podálica, biometría acorde a EG, peso fetal estimado 240 g. "
            "Discordancia de peso 2.1% (no patológica). Dos placentas independientes. "
            "Líquido amniótico en cantidad normal en ambos sacos.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        Paragraph(
            "PA 108/68 mmHg. FC 82 lpm. T° 36.5°C. Peso 64.0 kg. Talla 1.62 m. "
            "AU 26 cm (acorde a gestación gemelar). Edema MMII (-/-). "
            "LCF Feto A 148 lpm, LCF Feto B 152 lpm.",
            s["p"],
        ),
        Paragraph("LABORATORIOS (15/03/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "10.2", "g/dL", "Anemia leve gestacional"),
                ("Hematocrito", "31.0", "%", "Limítrofe bajo"),
                ("Glucosa basal", "84", "mg/dL", "Normal"),
                ("TSH", "1.9", "mUI/L", "Dentro de rango"),
                ("HIV (ELISA)", "No reactivo", "—", "Negativo"),
                ("Sífilis (RPR)", "No reactivo", "—", "Negativa"),
            ]
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Suplementación con sulfato ferroso 300 mg VO c/24 h. "
            "2. Ácido fólico y calcio según pauta de alto riesgo. "
            "3. Control quincenal a partir de semana 26. "
            "4. Eco obstétrica + Doppler cada 4 semanas para vigilar crecimiento y discordancia. "
            "5. Educación sobre signos de alarma específicos de gestación múltiple. "
            "6. Plan de parto a definir según evolución; cesárea si presentación no cefálica del Feto A.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 04 — RPM
# =========================================================================
def build_case_04(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA — EMERGENCIA", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Emergencia Gineco-Obstétrica",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", "30 años"),
                ("Estado civil:", "Casada"),
                ("Ocupación:", "Comerciante"),
                ("Fecha de ingreso:", "12/04/2026 02:30"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G1 P0. Primigesta. "
            "Niega antecedentes de cirugía pélvica o infecciones de transmisión sexual.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "12/08/2025"),
                ("FPP:", "19/05/2026"),
                ("EG actual (por FUM):", "34 semanas"),
                ("Motivo de ingreso:", "Ruptura prematura de membranas"),
                ("Tiempo de RPM al ingreso:", "8 horas"),
            ]
        ),
        Paragraph(
            "Paciente refiere pérdida de líquido por vía vaginal hace 8 horas, inicio súbito, "
            "líquido claro sin mal olor. Niega fiebre, escalofríos, dolor abdominal o sangrado. "
            "Movimientos fetales presentes y normales.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO AL INGRESO", s["h1"]),
        Paragraph(
            "PA 112/72 mmHg. FC 84 lpm. T° 36.8°C (afebril). Peso 71.0 kg. "
            "AU 32 cm. LCF 144 lpm. Dinámica uterina ausente. "
            "Especuloscopía: salida espontánea de líquido amniótico claro a través del orificio cervical. "
            "Test de helecho positivo. Tacto vaginal diferido para reducir riesgo de infección.",
            s["p"],
        ),
        Paragraph("LABORATORIOS DE INGRESO (12/04/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "11.6", "g/dL", "Dentro de rango"),
                ("Leucocitos", "9800", "/mm³", "Sin leucocitosis significativa"),
                ("PCR", "0.8", "mg/dL", "No elevada"),
                ("Glucosa", "88", "mg/dL", "Normal"),
                ("Urocultivo", "Pendiente", "—", "Tomado al ingreso"),
            ]
        ),
        Paragraph("ECOGRAFÍA RÁPIDA DE INGRESO", s["h1"]),
        Paragraph(
            "Feto único, vivo, presentación cefálica. Peso fetal estimado 2,150 g. "
            "ILA reducido (6 cm), compatible con oligoamnios secundario a RPM. "
            "Placenta posterior, no oclusiva. Doppler arteria umbilical normal.",
            s["p"],
        ),
        Paragraph("IMPRESIÓN DIAGNÓSTICA", s["h1"]),
        Paragraph(
            "1. Embarazo de 34 semanas por FUM. "
            "2. Ruptura prematura de membranas de 8 horas de evolución. "
            "3. Sin signos clínicos ni laboratoriales de corioamnionitis al momento.",
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Hospitalización en sala obstétrica. "
            "2. Antibioticoterapia profiláctica con ampicilina + eritromicina según protocolo de RPM pretérmino. "
            "3. Maduración pulmonar fetal con betametasona 12 mg IM c/24 h x 2 dosis. "
            "4. Manejo expectante: monitoreo materno (PA, FC, T° c/6 h, leucograma diario) "
            "y fetal (NST diario, eco semanal). "
            "5. Reevaluar inducción del parto a las 36-37 semanas o ante signos de infección o sufrimiento fetal.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 05 — diabetes gestacional
# =========================================================================
def build_case_05(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Consultorio de Alto Riesgo Obstétrico",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", "38 años"),
                ("Estado civil:", "Casada"),
                ("Ocupación:", "Independiente"),
                ("Fecha de elaboración:", "05/04/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G4 P3 (3 partos vaginales previos: 2014, 2017 y 2020). "
            "Recién nacido del último embarazo: 4,100 g (macrosómico). "
            "Antecedente familiar: madre con diabetes tipo 2.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "20/09/2025"),
                ("FPP:", "27/06/2026"),
                ("EG actual (por FUM):", "28 semanas"),
                ("Controles prenatales:", "6 al momento"),
                ("Diagnóstico nuevo:", "Diabetes gestacional"),
            ]
        ),
        Paragraph(
            "Paciente sin síntomas clásicos de hiperglucemia (polidipsia, poliuria, polifagia). "
            "Tamizaje universal de DG indicado por edad materna avanzada y antecedente de macrosomía.",
            s["p"],
        ),
        Paragraph("CURVA DE TOLERANCIA ORAL A LA GLUCOSA (75 g)", s["h1"]),
        _labs_table(
            [
                ("Glucosa ayuno", "105", "mg/dL", "Sobre umbral DG (>=92)"),
                ("Glucosa 1 h", "195", "mg/dL", "Sobre umbral DG (>=180)"),
                ("Glucosa 2 h", "165", "mg/dL", "Sobre umbral DG (>=153)"),
            ]
        ),
        Paragraph("OTROS LABORATORIOS (28/03/2026)", s["h1"]),
        _labs_table(
            [
                ("HbA1c", "6.4", "%", "Compatible con DG"),
                ("Hemoglobina", "12.1", "g/dL", "Dentro de rango"),
                ("Creatinina", "0.7", "mg/dL", "Normal"),
                ("TSH", "2.0", "mUI/L", "Dentro de rango"),
                ("Urocultivo", "Negativo", "—", "Sin ITU"),
            ]
        ),
        Paragraph("ECOGRAFÍA OBSTÉTRICA (28 SEMANAS)", s["h1"]),
        Paragraph(
            "Feto único, vivo, presentación cefálica. "
            "Peso fetal estimado: 1,850 g (percentil 90 — macrosomía fetal estimada). "
            "Líquido amniótico aumentado (ILA 22 cm — polihidramnios leve). "
            "Doppler arteria umbilical normal. Anatomía sin malformaciones.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        Paragraph(
            "PA 124/78 mmHg. FC 80 lpm. T° 36.6°C. Peso 82.5 kg. Talla 1.60 m. "
            "AU 31 cm. LCF 142 lpm. Edema MMII (-/-).",
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Plan nutricional con conteo de carbohidratos por nutricionista. "
            "2. Automonitoreo glucémico capilar: ayuno y postprandial 1 h, 4 mediciones diarias. "
            "3. Interconsulta con endocrinología para considerar inicio de insulina si metas no se logran en 1-2 semanas. "
            "4. Eco obstétrica + Doppler cada 4 semanas para vigilar crecimiento. "
            "5. Educación sobre signos de hipoglucemia e hiperglucemia. "
            "6. Reevaluar vía de parto cerca del término según peso fetal estimado.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 06 — anemia severa
# =========================================================================
def build_case_06(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Hospitalización Obstétrica",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", "22 años"),
                ("Estado civil:", "Conviviente"),
                ("Ocupación:", "Estudiante"),
                ("Fecha de ingreso:", "02/05/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G2 P1 (parto vaginal 2022, sin complicaciones). "
            "Antecedente de anemia leve en gestación previa, no completó tratamiento. "
            "Dieta referida pobre en hierro hemínico.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "01/10/2025"),
                ("FPP:", "08/07/2026"),
                ("EG actual (por FUM):", "30 semanas"),
                ("Motivo de ingreso:", "Anemia severa sintomática"),
                ("Controles prenatales:", "4 al momento"),
            ]
        ),
        Paragraph(
            "Paciente refiere cefalea persistente, palpitaciones de esfuerzo y fatiga severa en últimas 2 semanas. "
            "Tolerancia disminuida a actividad cotidiana. "
            "Niega sangrado vaginal, melena o hematuria. Movimientos fetales presentes.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO AL INGRESO", s["h1"]),
        Paragraph(
            "PA 100/60 mmHg. FC 108 lpm (taquicardia compensatoria). T° 36.5°C. "
            "Peso 58.0 kg. Palidez cutáneo-mucosa marcada. AU 28 cm. LCF 150 lpm. "
            "Auscultación cardíaca: soplo sistólico funcional grado 2/6 en foco aórtico. "
            "Sin signos de sobrecarga ni edema.",
            s["p"],
        ),
        Paragraph("LABORATORIOS (02/05/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "7.2", "g/dL", "Anemia severa"),
                ("Hematocrito", "22.0", "%", "Severamente bajo"),
                ("VCM", "72", "fL", "Microcitosis"),
                ("HCM", "23", "pg", "Hipocromía"),
                ("Ferritina", "8", "ng/mL", "Depleción severa de hierro"),
                ("Saturación transferrina", "10", "%", "Baja"),
                ("Reticulocitos", "1.2", "%", "Respuesta insuficiente"),
            ]
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Hierro endovenoso (hierro sacarosa o carboximaltosa) según disponibilidad y protocolo institucional. "
            "2. Estudios complementarios: hemograma seriado, función renal, frotis de sangre periférica, "
            "perfil de hierro completo. "
            "3. Reevaluación de necesidad de transfusión si Hb persiste <7 g/dL pese a hierro EV o si "
            "aparecen signos de descompensación cardiovascular. "
            "4. Monitoreo fetal: NST diario + eco con Doppler arteria cerebral media para descartar anemia fetal. "
            "5. Educación nutricional + suplementación oral combinada al alta. "
            "6. Interconsulta con hematología si etiología no se confirma como ferropénica.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 07 — control normal (versión con ruido tipo OCR/manuscrito)
# =========================================================================

_OCR_SUBS = {
    "l": ["1", "I"],
    "o": ["0"],
    "O": ["0"],
    "0": ["O"],
    "I": ["l", "1"],
    "5": ["S"],
    "S": ["5"],
    "B": ["8"],
    "8": ["B"],
    "G": ["6"],
    "Z": ["2"],
    "2": ["Z"],
}


def _ocr_noise(text: str, *, rate: float = 0.06, rng: random.Random) -> str:
    """Substituye un porcentaje pequeño de caracteres por confusiones tipo OCR.

    Pensado para emular escaneo de manuscrito procesado por OCR ruidoso.
    No se aplica al header sintético ni a fechas críticas — el extractor
    debe poder degradar grácilmente pero el ground truth refleja lo que
    el modelo puede inferir razonablemente.
    """
    out_chars: list[str] = []
    for ch in text:
        subs = _OCR_SUBS.get(ch)
        if subs and rng.random() < rate:
            out_chars.append(rng.choice(subs))
        else:
            out_chars.append(ch)
    return "".join(out_chars)


def build_case_07(out: Path) -> None:
    s = _styles()
    rng = random.Random(7)  # seed para reproducibilidad del ruido

    def n(text: str) -> str:
        return _ocr_noise(text, rate=0.07, rng=rng)

    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA (manuscrito digitalizado)", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Consultorio de Obstetricia",
            s["p"],
        ),
        Paragraph(
            "Nota: documento digitalizado a partir de manuscrito; calidad de OCR variable.",
            s["small"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", n("26 años")),
                ("Estado civil:", n("Conviviente")),
                ("Ocupación:", n("Asistente administrativa")),
                ("Fecha de elaboración:", "18/02/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            n(
                "Fórmula obstétrica: G1 P0. Primigesta. "
                "Menarquia: 12 años. Régimen catamenial regular previo. "
                "Sin antecedentes patológicos personales ni familiares relevantes."
            ),
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "20/09/2025"),
                ("FPP:", "27/06/2026"),
                ("EG actual (por FUM):", n("22 semanas")),
                ("Controles prenatales:", n("3 al momento")),
                ("Centro de control:", n("Mismo centro")),
            ]
        ),
        Paragraph(
            n(
                "Paciente refiere movimientos fetales presentes desde semana 19. "
                "No refiere sangrado, ni pérdida de líquido, ni contracciones. "
                "Sin signos de alarma al momento de la consulta."
            ),
            s["p"],
        ),
        Paragraph("LABORATORIOS (último control: 10/02/2026)", s["h1"]),
        _labs_table(
            [
                (n("Hemoglobina"), n("11.6"), "g/dL", n("Dentro de rango")),
                (n("TSH"), n("1.8"), "mUI/L", n("Dentro de rango")),
                (n("Glucosa basal"), n("86"), "mg/dL", n("Normal")),
                (n("HIV (ELISA)"), n("No reactivo"), "—", n("Negativo")),
                (n("Sífilis (RPR)"), n("No reactivo"), "—", n("Negativa")),
            ]
        ),
        Paragraph("ECOGRAFÍA DE LAS 20 SEMANAS (10/02/2026)", s["h1"]),
        Paragraph(
            n(
                "Feto único, vivo, en presentación cefálica al momento del estudio. "
                "Biometría acorde a edad gestacional. Peso fetal estimado 380 g. "
                "Placenta anterior, grado 0. ILA dentro de rango normal. "
                "Anatomía fetal sin anomalías estructurales observables."
            ),
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        Paragraph(
            n(
                "PA 108/68 mmHg. FC 80 lpm. T° 36.5°C. Peso 60.5 kg. Talla 1.60 m. "
                "AU 21 cm. LCF 146 lpm. Edema MMII (-/-)."
            ),
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            n(
                "1. Continuar suplementación con ácido fólico y calcio según pauta. "
                "2. Iniciar sulfato ferroso profiláctico 60 mg de hierro elemental VO c/24 h. "
                "3. Control prenatal en 4 semanas. "
                "4. Educación sobre signos de alarma obstétricos. "
                "5. Tamizaje de DG entre semanas 24-28."
            ),
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


CASES = [
    ("synthetic_case_02_preeclampsia.pdf", build_case_02),
    ("synthetic_case_03_gemelar.pdf", build_case_03),
    ("synthetic_case_04_rpm.pdf", build_case_04),
    ("synthetic_case_05_diabetes_gestacional.pdf", build_case_05),
    ("synthetic_case_06_anemia_severa.pdf", build_case_06),
    ("synthetic_case_07_manuscrito.pdf", build_case_07),
]


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for name, builder in CASES:
        out = OUT_DIR / name
        builder(out)
        size = out.stat().st_size
        print(f"wrote {out.relative_to(OUT_DIR.parent.parent.parent)} ({size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
