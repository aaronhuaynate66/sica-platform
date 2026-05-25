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

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

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


# =========================================================================
# Caso 08 — placenta previa total
# =========================================================================
def build_case_08(out: Path) -> None:
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
                ("Edad:", "33 años"),
                ("Estado civil:", "Casada"),
                ("Ocupación:", "Profesora"),
                ("Fecha de elaboración:", "08/04/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G3 P2 (1 parto vaginal 2018, 1 cesárea segmentaria 2021). "
            "Antecedente quirúrgico uterino sin complicaciones.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "26/09/2025"),
                ("FPP:", "03/07/2026"),
                ("EG actual (por FUM):", "31 semanas"),
                ("Controles prenatales:", "6 al momento"),
                ("Diagnóstico:", "Placenta previa total"),
            ]
        ),
        Paragraph(
            "Paciente refiere episodios intermitentes de sangrado vaginal escaso en últimas "
            "2 semanas. Niega dolor abdominal, contracciones o pérdida de líquido. "
            "Movimientos fetales presentes y normales.",
            s["p"],
        ),
        Paragraph("ECOGRAFÍA OBSTÉTRICA (08/04/2026)", s["h1"]),
        Paragraph(
            "Feto único, vivo, presentación cefálica. Peso fetal estimado 1,680 g. "
            "Placenta de inserción anterior cubriendo totalmente el orificio cervical interno — "
            "placenta previa total confirmada. ILA dentro de rango normal. "
            "Anatomía fetal sin malformaciones evidentes.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        Paragraph(
            "PA 116/72 mmHg. FC 84 lpm. T° 36.6°C. Peso 68.5 kg. "
            "AU 30 cm. LCF 144 lpm. Sin signos de sangrado activo al momento. "
            "Tacto vaginal diferido por dx de placenta previa.",
            s["p"],
        ),
        Paragraph("LABORATORIOS (06/04/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "10.5", "g/dL", "Anemia leve gestacional"),
                ("Hematocrito", "32.0", "%", "Limítrofe bajo"),
                ("Plaquetas", "245000", "/mm³", "Normal"),
                ("Glucosa basal", "85", "mg/dL", "Normal"),
                ("Tipo sanguíneo", "O Rh+", "—", "Confirmado"),
            ]
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Reposo relativo en domicilio. Evitar esfuerzo físico y relaciones sexuales. "
            "2. Control prenatal semanal con monitoreo de sangrado y bienestar fetal. "
            "3. Eco obstétrica de seguimiento cada 2-3 semanas. "
            "4. Hierro elemental 60 mg VO c/24 h. "
            "5. Cesárea programada a las 37 semanas según protocolo institucional. "
            "6. Ingreso inmediato ante sangrado moderado-severo o trabajo de parto.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 09 — amenaza de parto prematuro
# =========================================================================
def build_case_09(out: Path) -> None:
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
                ("Edad:", "25 años"),
                ("Estado civil:", "Conviviente"),
                ("Ocupación:", "Vendedora"),
                ("Fecha de ingreso:", "15/03/2026 08:45"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G1 P0. Primigesta. "
            "Niega antecedentes patológicos relevantes ni cirugía cervical.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "01/09/2025"),
                ("FPP:", "08/06/2026"),
                ("EG actual (por FUM):", "28 semanas"),
                ("Motivo de ingreso:", "Amenaza de parto prematuro"),
                ("Tiempo de evolución:", "6 horas"),
            ]
        ),
        Paragraph(
            "Paciente refiere contracciones uterinas regulares (4 en 30 minutos) desde hace "
            "6 horas. Niega sangrado vaginal o pérdida de líquido. Movimientos fetales "
            "presentes y normales. Refiere haber realizado esfuerzo físico el día previo.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO AL INGRESO", s["h1"]),
        Paragraph(
            "PA 110/70 mmHg. FC 88 lpm. T° 36.7°C (afebril). Peso 62.0 kg. "
            "AU 26 cm. LCF 148 lpm. Dinámica uterina: 3-4 contracciones en 10 min, "
            "intensidad moderada, duración 30-40 segundos. "
            "Tacto vaginal: cuello posterior, cerrado, sin modificaciones cervicales.",
            s["p"],
        ),
        Paragraph("EXÁMENES DE INGRESO (15/03/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "11.4", "g/dL", "Dentro de rango"),
                ("Leucocitos", "10200", "/mm³", "Limítrofe alto"),
                ("PCR", "0.6", "mg/dL", "No elevada"),
                ("Test fibronectina", "Negativo", "—", "Bajo riesgo parto en 14 días"),
                ("Urocultivo", "Pendiente", "—", "Tomado al ingreso"),
            ]
        ),
        Paragraph("IMPRESIÓN DIAGNÓSTICA", s["h1"]),
        Paragraph(
            "1. Embarazo de 28 semanas por FUM. "
            "2. Amenaza de parto prematuro sin modificaciones cervicales. "
            "3. Test de fibronectina negativo (bajo riesgo de parto en próximos 14 días).",
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Hospitalización en sala obstétrica por 24-48 horas para observación. "
            "2. Tocolítico de primera línea (nifedipino 20 mg VO de carga, luego 10 mg c/6 h). "
            "3. Maduración pulmonar fetal con betametasona 12 mg IM c/24 h x 2 dosis. "
            "4. Reposo en cama. Hidratación IV. "
            "5. Monitoreo materno (PA, FC, dinámica uterina c/2 h) y fetal (NST diario). "
            "6. Alta condicionada a cese de dinámica uterina y sin modificaciones cervicales.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 10 — oligohidramnios severo
# =========================================================================
def build_case_10(out: Path) -> None:
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
                ("Edad:", "36 años"),
                ("Estado civil:", "Casada"),
                ("Ocupación:", "Contadora"),
                ("Fecha de ingreso:", "18/04/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G2 P1 (parto vaginal 2022, sin complicaciones). "
            "Niega hipertensión, diabetes ni enfermedad renal.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "20/08/2025"),
                ("FPP:", "27/05/2026"),
                ("EG actual (por FUM):", "34 semanas"),
                ("Motivo de ingreso:", "Oligohidramnios severo"),
                ("Controles prenatales:", "7 al momento"),
            ]
        ),
        Paragraph(
            "Paciente refiere disminución leve de movimientos fetales en últimos 3 días. "
            "Niega pérdida de líquido vaginal, contracciones o sangrado. "
            "Eco de control reciente detectó ILA disminuido.",
            s["p"],
        ),
        Paragraph("ECOGRAFÍA OBSTÉTRICA (18/04/2026)", s["h1"]),
        Paragraph(
            "Feto único, vivo, presentación cefálica. Peso fetal estimado 2,050 g "
            "(percentil 25). ILA 4 cm (oligohidramnios severo, ILA <5 cm). "
            "Doppler arteria umbilical normal. Anatomía fetal sin malformaciones. "
            "Placenta posterior grado II.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO AL INGRESO", s["h1"]),
        Paragraph(
            "PA 118/74 mmHg. FC 80 lpm. T° 36.6°C. Peso 70.0 kg. "
            "AU 30 cm (acorde a EG). LCF 142 lpm. NST reactivo. "
            "Sin pérdida vaginal de líquido al examen especular. "
            "Test de helecho negativo.",
            s["p"],
        ),
        Paragraph("LABORATORIOS (18/04/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "12.2", "g/dL", "Dentro de rango"),
                ("Creatinina", "0.7", "mg/dL", "Normal"),
                ("Urea", "22", "mg/dL", "Normal"),
                ("Glucosa basal", "90", "mg/dL", "Normal"),
                ("Examen de orina", "Normal", "—", "Sin proteinuria"),
            ]
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Hospitalización para vigilancia materno-fetal. "
            "2. Maduración pulmonar fetal con betametasona 12 mg IM c/24 h x 2 dosis. "
            "3. Hidratación oral 2-3 L/día. Hidratación IV si tolerancia oral pobre. "
            "4. Monitoreo fetal con NST cada 24 horas y eco con ILA cada 48 horas. "
            "5. Considerar interrupción del embarazo a las 36-37 semanas si oligohidramnios "
            "persiste, o antes si aparecen signos de compromiso fetal. "
            "6. Interconsulta con perinatología.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 11 — hipotiroidismo descompensado
# =========================================================================
def build_case_11(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Consultorio Endocrino-Obstétrico",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", "29 años"),
                ("Estado civil:", "Casada"),
                ("Ocupación:", "Diseñadora gráfica"),
                ("Fecha de elaboración:", "12/02/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES PATOLÓGICOS", s["h1"]),
        Paragraph(
            "Diagnóstico previo de tiroiditis de Hashimoto desde 2019, en tratamiento con "
            "levotiroxina 75 mcg/día. Último control endocrino hace 8 meses. "
            "No otras enfermedades crónicas.",
            s["p"],
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G2 P0+1 (1 aborto espontáneo 2023 a las 8 semanas, "
            "sin causa identificada).",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "10/10/2025"),
                ("FPP:", "17/07/2026"),
                ("EG actual (por FUM):", "18 semanas"),
                ("Controles prenatales:", "4 al momento"),
                ("Diagnóstico nuevo:", "Hipotiroidismo descompensado en gestación"),
            ]
        ),
        Paragraph(
            "Paciente refiere fatiga progresiva, intolerancia al frío y aumento de peso "
            "inusual desde inicio del embarazo. Niega palpitaciones, temblor o pérdida de peso. "
            "Movimientos fetales aún no percibidos (acorde a EG).",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        Paragraph(
            "PA 108/68 mmHg. FC 64 lpm (bradicardia relativa). T° 36.2°C. Peso 65.5 kg "
            "(aumento de 3 kg en 6 semanas). Piel seca y fría. Bocio difuso grado I "
            "no doloroso. AU 16 cm. LCF 152 lpm.",
            s["p"],
        ),
        Paragraph("LABORATORIOS TIROIDEOS (10/02/2026)", s["h1"]),
        _labs_table(
            [
                ("TSH", "8.5", "mUI/L", "Elevada (meta gestacional <2.5)"),
                ("T4 libre", "0.7", "ng/dL", "Disminuida (rango 0.93-1.7)"),
                ("Anti-TPO", "245", "UI/mL", "Elevado — autoinmunidad confirmada"),
                ("T3 total", "85", "ng/dL", "Limítrofe bajo"),
            ]
        ),
        Paragraph("OTROS LABORATORIOS (10/02/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "11.9", "g/dL", "Dentro de rango"),
                ("Glucosa basal", "82", "mg/dL", "Normal"),
                ("HIV (ELISA)", "No reactivo", "—", "Negativo"),
                ("Sífilis (RPR)", "No reactivo", "—", "Negativa"),
            ]
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Ajuste de dosis de levotiroxina: aumentar a 125 mcg/día (incremento del "
            "60-80% sobre dosis pregestacional según guías ATA). "
            "2. Control de TSH y T4 libre en 4 semanas. Meta TSH gestacional <2.5 mUI/L. "
            "3. Educación sobre adherencia y toma de levotiroxina en ayunas. "
            "4. Eco obstétrica del segundo trimestre programada en 2 semanas. "
            "5. Suplementación con yodo + ácido fólico + hierro según pauta de alto riesgo. "
            "6. Interconsulta con endocrinología.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 12 — infección urinaria sintomática
# =========================================================================
def build_case_12(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Consultorio Obstétrico",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", "31 años"),
                ("Estado civil:", "Casada"),
                ("Ocupación:", "Enfermera"),
                ("Fecha de elaboración:", "22/01/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G1 P0. Primigesta. "
            "Antecedente de 2 episodios de ITU en últimos 12 meses (pregestacional).",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "05/10/2025"),
                ("FPP:", "12/07/2026"),
                ("EG actual (por FUM):", "16 semanas"),
                ("Controles prenatales:", "3 al momento"),
                ("Diagnóstico:", "Infección urinaria sintomática"),
            ]
        ),
        Paragraph(
            "Paciente refiere disuria, polaquiuria y urgencia miccional desde hace 4 días. "
            "Lumbalgia leve bilateral. Niega fiebre, escalofríos, náuseas o vómitos. "
            "Movimientos fetales aún no percibidos. Sin signos de irritación uterina.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        Paragraph(
            "PA 112/70 mmHg. FC 82 lpm. T° 36.8°C (afebril). Peso 60.5 kg. "
            "Puño-percusión lumbar negativa bilateral. Sin signos de pielonefritis. "
            "AU 14 cm. LCF 156 lpm.",
            s["p"],
        ),
        Paragraph("LABORATORIOS (22/01/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "12.0", "g/dL", "Dentro de rango"),
                ("Leucocitos", "9400", "/mm³", "Normal"),
                ("PCR", "1.2", "mg/dL", "Discretamente elevada"),
                ("Examen de orina", "Leucocitos 30-40/c", "—", "Piuria significativa"),
                ("Urocultivo", "E. coli >100,000", "UFC/mL", "Crecimiento significativo"),
                ("Antibiograma", "Sensible nitrofur.", "—", "Resistente a TMP-SMX"),
            ]
        ),
        Paragraph("IMPRESIÓN DIAGNÓSTICA", s["h1"]),
        Paragraph(
            "1. Embarazo de 16 semanas por FUM. "
            "2. ITU baja sintomática (cistitis aguda) por E. coli. "
            "3. Sin signos clínicos de pielonefritis aguda.",
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Nitrofurantoína 100 mg VO c/8 h por 7 días (sensible según antibiograma, "
            "categoría B en gestación, evitar cerca del término). "
            "2. Hidratación abundante (>2 L/día). "
            "3. Educación sobre signos de alarma (fiebre, vómitos, dolor lumbar severo). "
            "4. Urocultivo de control 7-10 días post-tratamiento. "
            "5. Profilaxis con dosis baja si recurrencia. "
            "6. Control prenatal regular en 2 semanas.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 13 — gestante adolescente con vulnerabilidad psicosocial
# Contiene texto sensible (referencia a contexto familiar) — verificar que el
# extractor procesa campos clínicos sin filtrar por sensibilidad del caso.
# =========================================================================
def build_case_13(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Consultorio de Adolescentes",
            s["p"],
        ),
        Paragraph(
            "Nota: caso con vulnerabilidad psicosocial. Información clínica completa; "
            "datos sensibles del entorno familiar agregados en este registro sintético.",
            s["small"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", "19 años"),
                ("Estado civil:", "Soltera"),
                ("Ocupación:", "Estudiante secundaria"),
                ("Fecha de elaboración:", "28/02/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G1 P0. Primigesta adolescente. Menarquia 12 años. "
            "Régimen catamenial irregular previo a la gestación.",
            s["p"],
        ),
        Paragraph("CONTEXTO PSICOSOCIAL", s["h1"]),
        Paragraph(
            "Embarazo no planificado. Paciente refiere situación familiar conflictiva en "
            "últimos meses, incluyendo antecedente de violencia intrafamiliar (verbal y "
            "ocasionalmente física) por parte de la pareja, situación que se encuentra "
            "actualmente en proceso de denuncia. Vive con la madre. Sin red de apoyo de la "
            "pareja. Estado afectivo lábil pero con conciencia de embarazo y disposición a "
            "control prenatal.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "20/11/2025"),
                ("FPP:", "27/08/2026"),
                ("EG actual (por FUM):", "14 semanas"),
                ("Controles prenatales:", "2 al momento"),
                ("Estado emocional:", "Lábil — requiere apoyo psicosocial"),
            ]
        ),
        Paragraph(
            "Paciente refiere síntomas digestivos leves de primer trimestre (náuseas matutinas) "
            "ya en resolución. Sin signos de alarma obstétricos. Movimientos fetales aún no "
            "percibidos (acorde a EG).",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        Paragraph(
            "PA 100/64 mmHg. FC 84 lpm. T° 36.5°C. Peso 52.0 kg. Talla 1.58 m. "
            "Estado nutricional bajo el ideal. AU 12 cm. LCF 158 lpm. "
            "Sin signos de violencia física actuales al examen.",
            s["p"],
        ),
        Paragraph("LABORATORIOS (15/02/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "11.2", "g/dL", "Anemia leve gestacional"),
                ("TSH", "2.0", "mUI/L", "Dentro de rango"),
                ("Glucosa basal", "78", "mg/dL", "Normal"),
                ("HIV (ELISA)", "No reactivo", "—", "Negativo"),
                ("Sífilis (RPR)", "No reactivo", "—", "Negativa"),
                ("Hepatitis B", "No reactivo", "—", "Negativo"),
            ]
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Control prenatal con protocolo estándar de adolescente (más controles, foco nutricional). "
            "2. Derivación a Servicio Social del establecimiento para evaluación de red de apoyo "
            "y orientación legal sobre denuncia de violencia. "
            "3. Interconsulta con Psicología para acompañamiento durante la gestación. "
            "4. Suplementación con ácido fólico, hierro y calcio. "
            "5. Educación nutricional individualizada. "
            "6. Próximo control en 3 semanas con evaluación de estado emocional.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 14 — caso complejo multipatología
# Edge case difícil: edad materna avanzada + multiparidad + DM + HTA crónica.
# Múltiples problemas activos, muchos labs, plan complejo.
# =========================================================================
def build_case_14(out: Path) -> None:
    s = _styles()
    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA — ALTO RIESGO", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Hospitalización Obstétrica de Alto Riesgo",
            s["p"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", "41 años"),
                ("Estado civil:", "Casada"),
                ("Ocupación:", "Ama de casa"),
                ("Fecha de ingreso:", "20/04/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES PATOLÓGICOS", s["h1"]),
        Paragraph(
            "Hipertensión arterial crónica diagnosticada hace 5 años, en tratamiento con "
            "metildopa 250 mg c/8 h desde inicio del embarazo (previamente recibía losartán, "
            "suspendido al confirmarse gestación). "
            "Diabetes mellitus tipo 2 diagnosticada hace 3 años, controlada con dieta y "
            "metformina 850 mg c/12 h continuada en gestación. "
            "Sobrepeso pregestacional (IMC 28).",
            s["p"],
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            "Fórmula obstétrica: G5 P4 (4 hijos vivos — 2 partos vaginales 2010 y 2013, "
            "2 cesáreas segmentarias 2017 y 2020, esta última por cesárea anterior + macrosomía). "
            "Sin antecedente de preeclampsia ni diabetes gestacional. Lactancia previa exitosa.",
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "10/08/2025"),
                ("FPP:", "17/05/2026"),
                ("EG actual (por FUM):", "36 semanas"),
                ("Motivo de ingreso:", "Vigilancia materno-fetal por riesgo múltiple"),
                ("Controles prenatales:", "9 al momento"),
            ]
        ),
        Paragraph(
            "Paciente refiere cefalea leve intermitente en últimas 72 horas que cede con "
            "reposo. Niega visión borrosa, epigastralgia o edema súbito. Movimientos fetales "
            "presentes. Adherencia al tratamiento antihipertensivo y antidiabético verificada.",
            s["p"],
        ),
        Paragraph("EXAMEN FÍSICO AL INGRESO", s["h1"]),
        Paragraph(
            "PA 145/92 mmHg (confirmada en 2 tomas — limítrofe alta, requiere ajuste). "
            "FC 86 lpm. T° 36.7°C. Peso 84.0 kg. Talla 1.58 m. IMC actual 33.6. "
            "Edema MMII (+/-) leve hasta tobillos. AU 33 cm. LCF 144 lpm. "
            "Sin signos clínicos de preeclampsia severa.",
            s["p"],
        ),
        Paragraph("LABORATORIOS (20/04/2026)", s["h1"]),
        _labs_table(
            [
                ("Hemoglobina", "11.5", "g/dL", "Limítrofe"),
                ("Plaquetas", "215000", "/mm³", "Normal"),
                ("Creatinina", "0.8", "mg/dL", "Normal"),
                ("Urea", "26", "mg/dL", "Normal"),
                ("Glucosa basal", "110", "mg/dL", "Sobre meta gestacional"),
                ("HbA1c", "6.2", "%", "Sobre meta (<6.0)"),
                ("Proteinuria 24 h", "0.4", "g/24 h", "No significativa"),
                ("AST (TGO)", "28", "U/L", "Normal"),
                ("ALT (TGP)", "32", "U/L", "Normal"),
                ("LDH", "280", "U/L", "Normal"),
            ]
        ),
        Paragraph("ECOGRAFÍA OBSTÉTRICA (20/04/2026)", s["h1"]),
        Paragraph(
            "Feto único, vivo, presentación cefálica. Peso fetal estimado 3,150 g "
            "(percentil 88 — macrosomía limítrofe). ILA 18 cm (limítrofe alto). "
            "Placenta anterior grado II-III. Doppler arterias uterinas y umbilical normales. "
            "Doppler de arteria cerebral media normal.",
            s["p"],
        ),
        Paragraph("IMPRESIÓN DIAGNÓSTICA", s["h1"]),
        Paragraph(
            "1. Embarazo de 36 semanas por FUM. "
            "2. Hipertensión arterial crónica con control limítrofe — descartar superposición de preeclampsia. "
            "3. Diabetes mellitus tipo 2 pregestacional con control glucémico subóptimo (HbA1c 6.2%). "
            "4. Macrosomía fetal limítrofe (PFE percentil 88). "
            "5. Edad materna avanzada + cesárea anterior x2 + gran multípara. "
            "6. Obesidad (IMC pregestacional 28, actual 33.6).",
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            "1. Hospitalización en unidad de alto riesgo obstétrico para vigilancia. "
            "2. Ajuste de antihipertensivos: agregar nifedipino retard 10 mg c/12 h. "
            "3. Optimización de control glucémico: considerar agregar insulina basal nocturna. "
            "4. NST cada 12 horas. Doppler fetal cada 48 horas. "
            "5. Maduración pulmonar fetal si se decidiera cesárea antes de 37 semanas. "
            "6. Programar cesárea segmentaria a las 38-39 semanas por antecedente de cesárea "
            "anterior x2 + macrosomía estimada + paridad alta. "
            "7. Profilaxis tromboembólica con HBPM por factores de riesgo combinados. "
            "8. Interconsulta con cardiología, endocrinología y anestesiología.",
            s["p"],
        ),
    ]
    story += _footer_block(s)
    _build_doc(out, story)


# =========================================================================
# Caso 15 — PDF "escaneado de baja calidad"
# Mismo perfil clínico que case_01 con ruido OCR más agresivo que case_07
# para emular escaneo borroso/degradado. Stress-test del extractor.
# =========================================================================
def build_case_15(out: Path) -> None:
    s = _styles()
    rng = random.Random(15)  # seed para reproducibilidad

    def n(text: str) -> str:
        # Ruido OCR más agresivo que case_07 (10% vs 7%) para emular escaneo borroso.
        return _ocr_noise(text, rate=0.10, rng=rng)

    story: list = []
    story += _header_block(s)
    story += [
        Paragraph("HISTORIA CLÍNICA OBSTÉTRICA (escaneo de baja calidad)", s["title"]),
        Paragraph(
            "Centro Materno-Infantil (sintético) — Consultorio Obstétrico (documento digitalizado)",
            s["p"],
        ),
        Paragraph(
            "Nota: este PDF emula un escaneado de baja calidad. Caracteres legibles "
            "mecánicamente pero con confusiones tipo OCR frecuentes (l↔1, O↔0, S↔5, etc.).",
            s["small"],
        ),
        Paragraph("FILIACIÓN", s["h1"]),
        _kv_table(
            [
                ("Nombre:", "PACIENTE SINTÉTICA - NO REAL"),
                ("Edad:", n("32 años")),
                ("Estado civil:", n("Casada")),
                ("Ocupación:", n("Ingeniera")),
                ("Fecha de elaboración:", "10/04/2026"),
            ]
        ),
        Paragraph("ANTECEDENTES GINECO-OBSTÉTRICOS", s["h1"]),
        Paragraph(
            n(
                "Fórmula obstétrica: G2 P1 (1 cesárea segmentaria, 2022, por desproporción "
                "céfalo-pélvica, sin complicaciones posteriores). Lactancia previa exitosa."
            ),
            s["p"],
        ),
        Paragraph("GESTACIÓN ACTUAL", s["h1"]),
        _kv_table(
            [
                ("FUM:", "15/09/2025"),
                ("FPP:", "22/06/2026"),
                ("EG actual (por FUM):", n("28 semanas 2 días")),
                ("Controles prenatales:", n("5 al momento")),
            ]
        ),
        Paragraph(
            n(
                "Paciente refiere movimientos fetales presentes y normales. "
                "Sin signos de alarma obstétricos al momento del control."
            ),
            s["p"],
        ),
        Paragraph("LABORATORIOS (último control: 02/04/2026)", s["h1"]),
        _labs_table(
            [
                (n("Hemoglobina"), n("10.8"), "g/dL", n("Anemia leve gestacional")),
                (n("TSH"), n("2.1"), "mUI/L", n("Dentro de rango")),
                (n("Glucosa basal"), n("92"), "mg/dL", n("Normal")),
                (n("HIV (ELISA)"), n("No reactivo"), "—", n("Negativo")),
                (n("Sífilis (RPR)"), n("No reactivo"), "—", n("Negativa")),
            ]
        ),
        Paragraph("EXAMEN FÍSICO ACTUAL", s["h1"]),
        Paragraph(
            n(
                "PA 110/70 mmHg. FC 78 lpm. T° 36.6°C. Peso 68.5 kg. "
                "AU 27 cm. LCF 142 lpm."
            ),
            s["p"],
        ),
        Paragraph("PLAN", s["h1"]),
        Paragraph(
            n(
                "1. Continuar sulfato ferroso 300 mg VO c/24 h por anemia leve. "
                "2. Control prenatal en 4 semanas. "
                "3. Cesárea programada a las 39 semanas por cesárea previa."
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
    ("synthetic_case_08_placenta_previa.pdf", build_case_08),
    ("synthetic_case_09_amenaza_parto_prematuro.pdf", build_case_09),
    ("synthetic_case_10_oligohidramnios.pdf", build_case_10),
    ("synthetic_case_11_hipotiroidismo.pdf", build_case_11),
    ("synthetic_case_12_itu.pdf", build_case_12),
    ("synthetic_case_13_adolescente_vulnerable.pdf", build_case_13),
    ("synthetic_case_14_caso_complejo.pdf", build_case_14),
    ("synthetic_case_15_pdf_escaneado_borroso.pdf", build_case_15),
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
