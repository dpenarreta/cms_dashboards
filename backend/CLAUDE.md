# Backend (Django + DRF)

Hereda `../CLAUDE.md` (comandos base, contrato de error, catálogo de permisos). Esto cubre solo lo
propio de la capa backend.

## Comandos

- Test de una app: `python manage.py test apps.audit` / `python manage.py test cartera`
- Crear migración: `python manage.py makemigrations <app>`
- Shell: `python manage.py shell`
- Limpieza de archivos temporales huérfanos: `python manage.py clean_temp_uploads --horas 24`
- Recalcular el contenido de dashboards ya existentes (simula salvo `--aplicar`):
  `python manage.py reprocesar_dashboards [--aplicar] [--dashboard ID] [--detalle]`

- Reconstruir el Dashboard Directorio con un archivo (simula salvo `--aplicar`):
  `python manage.py sembrar_directorio_cartera --archivo "ruta.xlsx" [--aplicar]`
  (o `--desde-carga`, para releer la última carga procesada en vez de un archivo — es lo que se
  usa en producción, donde los datos vienen de un procedimiento y no hay ningún `.xlsx`)
- Congelar/descongelar la estructura de un dashboard:
  `python manage.py bloquear_dashboard <dashboard_id> [--desbloquear]` — ver
  `@.claude/rules/dashboards.md`

Los dos comandos periódicos (`actualizar_fuentes_bd`, `clean_temp_uploads`) se programan con el
Programador de tareas del sistema operativo, no con un scheduler propio de la app — ver
`docs/tareas_programadas.md` y `backend/scripts/`.

## Apps instaladas (`config/settings.py::INSTALLED_APPS`)

`cartera` (original, en la raíz de `backend/`, no bajo `apps/` — decisión deliberada, ver
`docs/integracion/decisions.md` #1: moverla arriesgaba las migraciones/`app_label` sin beneficio)
+ `apps.core`, `apps.audit`, `apps.permissions`, `apps.authentication`, `apps.users`,
`apps.roles`, `apps.branding`. Cada una tiene su propio `CLAUDE.md`.

## Arquitectura de capas

- Vistas (`views.py`) reciben el request, validan con serializers y delegan en `services/`. No
  pongas lógica de negocio en una vista ni en un serializer.
- `services/` retorna instancias de modelo o estructuras simples — no hay capa DTO separada en
  este proyecto (a diferencia de otros proyectos Django, no la introduzcas aquí sin necesidad).
- Todo servicio que muta datos recibe `actor=` (el usuario que ejecuta la acción) para poder
  auditar quién hizo el cambio.

## Base de datos

- SQL Server vía `mssql-django` (`ENGINE = 'mssql'`) por defecto; `DB_ENGINE=sqlite` es la única
  alternativa soportada para desarrollo sin SQL Server — el ORM abstrae el resto, no condiciones
  el código a un motor específico.
- IMPORTANT: nunca edites una migración ya mergeada a `main`. `cartera/migrations/` (13
  migraciones, con seeds/backfills reales) y `apps/*/migrations/` pueden estar aplicadas en un
  entorno real — crea una migración nueva siempre.

## Errores y permisos

- Lanza `cartera.exceptions.CarteraError(mensaje, codigo='ALGO', detalles={})` para cualquier
  error de negocio esperado (no un `raise Exception` genérico) — el `EXCEPTION_HANDLER` global lo
  traduce a `{"error", "mensaje", "detalles"}` con 400.
- Protege vistas con `apps.permissions.permissions.require_permission('modulo.accion')`, no con
  chequeos manuales de `request.user.groups`. Detalle en `@.claude/rules/security.md`.

## Pruebas

`django.test.TestCase`/`APITestCase` (no pytest, decisión 12 de `decisions.md`). Detalle de
convenciones y trampas en `@.claude/rules/testing.md`.
