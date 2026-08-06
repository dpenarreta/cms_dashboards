# tests/ (criterios de aceptación Gherkin)

Hereda `../CLAUDE.md`. Esta carpeta **no** es una suite ejecutable — no hay `pytest-bdd` ni
runner de Gherkin configurado (decisión 12, `docs/integracion/decisions.md`: un solo framework de
pruebas, Django `TestCase`/Vitest). No intentes correr estos `.feature` con `behave`/`pytest-bdd`
sin confirmarlo primero, no está montado.

## Qué contiene

- `qa/*.feature` — criterios de aceptación en Gherkin, documentan el comportamiento esperado.
- `qa/acceptance-criteria-traceability*.md` — mapeo criterio → prueba automatizada real
  (`backend/.../tests.py`, `frontend/src/tests/*.test.jsx`) o, si no es automatizable en jsdom
  (hover de tooltip, arrastre real de `dnd-kit`, viewport móvil real), verificación manual
  documentada ahí.
- `qa/test-execution-report*.md` — resultado de la última ejecución completa registrada.

## Reglas

- Si agregas o cambias un comportamiento que ya tiene un criterio Gherkin asociado, actualiza el
  `.feature` correspondiente y agrega la fila en el archivo de trazabilidad — no dejes el
  criterio desactualizado respecto al código real.
- La prueba automatizada real (backend/frontend) es la que se ejecuta en CI/validación — el
  `.feature` es documentación legible por negocio, no un test que se corra directamente.
