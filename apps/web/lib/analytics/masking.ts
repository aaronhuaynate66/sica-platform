/**
 * Atributos de masking para PHI / datos extraídos / contenido sensible.
 *
 * Convención:
 * - `data-clarity-mask="true"`: Microsoft Clarity oculta el contenido en las
 *   grabaciones (session replay). Texto se reemplaza por bloques opacos.
 * - `data-no-track="true"`: convención interna; no es procesada por GA4
 *   directamente, pero sirve como flag semántico para auditoría y para que
 *   nuestros propios eventos `trackEvent` no incluyan el contenido como
 *   param. También documenta intención para revisión humana.
 *
 * Qué se enmascara y por qué:
 *
 * | Elemento                                    | Por qué                              |
 * |---------------------------------------------|--------------------------------------|
 * | Edad / EG / FUM / FPP (datos demográficos) | Pueden ser cuasi-identificadores en combinación |
 * | Problemas activos, riesgos, plan           | Información clínica del paciente     |
 * | Lab values + analito                       | Resultados clínicos sensibles        |
 * | Notes summary                              | Narrativa clínica completa           |
 * | EvidenceModal `<pre>` con texto verbatim   | Fragmento literal del documento (puede incluir PHI residual aunque sea sintético) |
 * | EditableField inputs / textareas           | Lo que el usuario edita ES dato clínico |
 * | EditsIndicator diff (original/nuevo)       | Muestra valores antes y después      |
 * | Iframe del PDF                             | El PDF entero, incluido cualquier PHI que pueda contener en uploads en vivo |
 *
 * Aplicar `applyMaskingProps()` como spread en JSX:
 *
 *   <span {...applyMaskingProps()}>{patient_age}</span>
 *
 * Helpers `withMaskingProps()` y `MaskedSpan` están en este módulo para
 * el uso conveniente.
 */

export const MASK_ATTRIBUTES = {
  CLARITY: "data-clarity-mask",
  GA: "data-no-track",
} as const;

/**
 * Devuelve el objeto de props que aplica masking. Spread en JSX:
 *
 *   <td {...applyMaskingProps()}>...</td>
 */
export function applyMaskingProps(): {
  "data-clarity-mask": "true";
  "data-no-track": "true";
} {
  return {
    "data-clarity-mask": "true",
    "data-no-track": "true",
  };
}
