# docs/

Hereda `../CLAUDE.md`. Documentación técnica — no la conviertas en una copia del código; solo
decisiones y contexto que el código no explica por sí solo.

## Qué actualizar y cuándo

- `integracion/decisions.md` — registro de decisiones de arquitectura (ADR informal), formato
  Contexto/Opciones/Alternativa seleccionada/Motivo/Impacto/Archivos afectados. Agrega una entrada
  nueva cuando tomes una decisión de arquitectura no trivial (elegir entre dos enfoques, introducir
  o descartar una dependencia, cambiar un contrato compartido) — no la reescribas retroactivamente,
  las decisiones pasadas quedan como historial aunque ya no apliquen del todo.
- `audit/unified_audit.md`, `authentication/password_recovery.md`, `frontend/bootstrap_theme.md`,
  `dashboard.md` — documentación de features específicas ya construidas, con el razonamiento
  detrás de decisiones no obvias. Actualízalos si cambias el comportamiento que describen; no
  crees un documento nuevo para una variación menor de un feature ya documentado.
- `api-reference.md` — debe reflejar los endpoints reales. Si agregas/cambias un endpoint,
  actualízalo junto con la tabla de endpoints del `README.md` raíz (ambos listan lo mismo, no
  dejes que diverjan).

## Reglas

- No dupliques en un documento nuevo algo que ya está en `README.md` o en un `CLAUDE.md` — enlaza
  en vez de copiar.
- Los `.jpg`/capturas de pantalla en esta carpeta corresponden al archivo sintético de pruebas
  (`backend/cartera/tests/fixtures/cartera_ejemplo.xlsx`), nunca a datos reales de clientes — no
  agregues capturas generadas con datos reales.
