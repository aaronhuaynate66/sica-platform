# Política de seguridad — SICA

**Versión:** 0.1
**Última actualización:** 2026-05-21
**Estado del producto:** pre-producto. No hay ningún sistema de SICA en producción ni procesando PHI real a la fecha de este documento.

---

## Cómo reportar una vulnerabilidad

SICA acoge la divulgación responsable de vulnerabilidades de seguridad. Si descubrís una vulnerabilidad, **no abras un issue público en GitHub.** En su lugar:

1. Envianos un correo a **security@sica.pe** `[TODO — confirmar buzón corporativo definitivo y rotar antes de R1]`.
2. Incluí en el reporte:
   - Descripción del problema y su impacto potencial.
   - Pasos de reproducción (proof-of-concept si es posible).
   - Versión, commit hash o entorno donde se observó.
   - Vector de explotación.
   - Si querés, propuesta de mitigación.
3. No divulgues públicamente la vulnerabilidad hasta que SICA confirme una remediación o pasen 90 días desde el reporte inicial, lo que ocurra primero.
4. SICA se compromete a tratar el reporte con confidencialidad y a reconocer la contribución del reportante (si lo desea) en notas de release o página de agradecimientos.

## Tiempos de respuesta esperados

Estos tiempos son objetivos operacionales, no garantías contractuales. Pueden ajustarse según la severidad del reporte.

| Acción | Plazo objetivo |
|---|---:|
| Acuse de recibo del reporte | 3 días hábiles |
| Triage inicial y clasificación de severidad | 7 días hábiles |
| Comunicación de plan de remediación | 14 días hábiles |
| Remediación de severidad crítica | 30 días calendario |
| Remediación de severidad alta | 60 días calendario |
| Remediación de severidad media/baja | 90 días calendario |

## Qué consideramos vulnerabilidad de seguridad

Reportes apropiados para este canal:

- **Fuga o exposición de PHI** (información de salud identificable de pacientes), incluso si es teórica o demostrada en datos sintéticos.
- **Bypass de autenticación o autorización** en cualquier componente de SICA.
- **Escalamiento de privilegios** dentro del sistema.
- **Ejecución remota de código** o inyección (SQL, comando, prompt) en componentes que procesan datos clínicos.
- **Exposición de secretos** (API keys, credenciales, llaves de cifrado) en código, logs o artefactos públicos.
- **Vulnerabilidades en la cadena de suministro** (dependencias maliciosas, compromisos de paquetes).
- **Fallas criptográficas** (cifrado débil, llaves expuestas, mal uso de TLS).
- **Prompt injection** que permita exfiltrar PHI o alterar outputs clínicos sin consentimiento.
- **Cross-tenant data leakage** en arquitecturas multi-tenant.
- **Configuraciones inseguras** en infraestructura (buckets públicos, permisos IAM excesivos).

## Qué NO consideramos vulnerabilidad de seguridad

Estos reportes deben ir por los canales regulares de GitHub Issues, no por el canal de seguridad:

- Bugs de funcionalidad sin impacto en seguridad.
- Problemas de UX, copy, traducciones.
- Pedidos de features.
- Outputs clínicamente incorrectos (esos van por el flujo de calidad clínica, no de seguridad).
- Vulnerabilidades de dependencias sin path de explotación demostrable en SICA.
- Reportes de scanners automatizados sin verificación manual.
- Vulnerabilidades en software de terceros que SICA no controla directamente (en ese caso, repórtalo al upstream).

## Alcance

Esta política aplica a:

- El código en este repositorio (`sica-platform`).
- Servicios desplegados oficialmente por SICA (cuando existan).
- Documentación de seguridad y políticas asociadas.

Esta política **no aplica** a:

- Forks no oficiales o despliegues por terceros.
- Servicios de terceros que SICA integra (Google Cloud, Anthropic, etc.) — repórtalos al proveedor.
- Repositorios personales de contribuidores.

## Disclaimer

SICA es un proyecto **pre-producto** en Fase 1 (consolidación estratégica). A la fecha de esta política:

- No hay ningún sistema de SICA desplegado en producción.
- No se está procesando PHI real de pacientes.
- Las políticas de seguridad documentadas en este repo son normativas internas que se aplicarán una vez que se inicie el procesamiento de datos reales con el partner fundador.

Esto **no** disminuye la importancia de los reportes de seguridad: queremos que el sistema esté endurecido antes de tocar el primer dato real, no después.

## Documentación de detalle

Para detalle técnico-operativo de las políticas de seguridad de SICA, ver:

- [`docs/security/data-handling.md`](docs/security/data-handling.md) — Manejo de PHI, cifrado, acceso, retención, desidentificación, routing de modelos AI.
- [`docs/security/ley-29733-compliance.md`](docs/security/ley-29733-compliance.md) — Mapeo de obligaciones de Ley 29733 (Protección de Datos Personales del Perú) al estado actual de SICA.
- [`docs/security/incident-response.md`](docs/security/incident-response.md) — Plan de respuesta a incidentes, plazos legales, playbooks.
- [`docs/security/threat-model.md`](docs/security/threat-model.md) — Modelo de amenazas STRIDE y vectores específicos de healthtech AI.
- [`docs/decisions/0003-security-and-phi-policy.md`](docs/decisions/0003-security-and-phi-policy.md) — ADR que formaliza la adopción de estas políticas.

## Histórico de divulgaciones

Ninguna a la fecha (producto pre-deploy).
