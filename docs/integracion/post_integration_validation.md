# Validación post-integración — criterios de aceptación de la sección 31 del prompt

Checklist honesto contra la lista de "no consideres terminada la tarea mientras..." del prompt
original de integración. Cada fila indica evidencia concreta, no una autoevaluación genérica.

| Criterio de "no terminado" | ¿Se cumple la condición de bloqueo? | Evidencia |
|---|---|---|
| No existe un informe de diferencias | No — existe | `docs/integracion/skelleton_base_comparison.md` |
| No existe una matriz de migración | No — existe | `docs/integracion/file_migration_matrix.md` |
| Existen funcionalidades duplicadas | No | Un solo sistema de auth/usuarios/roles/permisos. `DashboardAuditLog` vs. `apps.core.AuditLog` coexisten, pero son dominios distintos (documentado en `decisions.md` #9), no una duplicidad accidental |
| Existen dos sistemas de autenticación | No | Solo `apps.authentication` (JWT); `cms_dashboards` no tenía ninguno antes |
| Existen dos modelos principales de usuario | No | `AUTH_USER_MODEL = 'users.User'` único, `cms_dashboards` nunca usó el modelo por defecto de Django en producción |
| Los permisos solo se validan en frontend | No | `cartera/tests/test_dashboard_authorization.py::test_autenticado_sin_permiso_dashboard_view_devuelve_403` prueba el rechazo real del backend, no solo el ocultamiento de un enlace; verificado también manualmente (un usuario sin `permisos.ver` recibe 403 real al pedir `/api/permissions/`, no solo un enlace oculto) |
| La landing pública deja de funcionar | No aplica | Ninguno de los dos proyectos tenía una landing real antes de integrar (confirmado leyendo `App.jsx` antes de empezar); se documentó como diferida, no como regresión |
| Algún dashboard existente deja de funcionar | No | Las 77 pruebas originales de `cartera/tests/test_api.py` (KPIs, gráficos, filtros, matriz, exportación, paginación) siguen en verde sin tocar sus aserciones de negocio; verificado además manualmente en navegador |
| Existen errores de compilación | No | `npm run build`-equivalente (Vite dev server arranca sin errores en cada verificación manual); `python manage.py check` sin errores en cada fase |
| Existen errores de consola | No | Verificado en cada sesión de navegador (login, dashboard, administración, configuración institucional) vía `read_console_messages` |
| Existen migraciones incompatibles sin documentar | No | El único conflicto real (`AUTH_USER_MODEL` vs. historial ya aplicado) está documentado en `migration_report.md` con la solución aplicada (recreación de la base de desarrollo, autorizada explícitamente por el usuario) |
| Existen pruebas críticas fallidas | No | 144/144 backend, 164/164 frontend al cierre de la sesión |
| Existen credenciales dentro del código | No | `.env`/`.env.example` no incluyen secretos reales versionados; `SECRET_KEY`/`JWT_SECRET_KEY` se leen de variables de entorno |
| El menú no respeta los permisos | No | `AdminSidebar.test.jsx` prueba que solo se listan los módulos con permiso; el backend vuelve a validar cada endpoint independientemente del menú |
| El administrador general no puede visualizar todos los módulos autorizados | No | `test_rol_administrador_general_tiene_el_catalogo_completo` (20/20 permisos), `test_administrador_general_ve_todos_los_dashboards_autorizados` |
| Los usuarios pueden consultar dashboards no autorizados | No | `test_usuario_sin_permiso_no_ve_ningun_dashboard` (lista vacía) y `test_autenticado_sin_permiso_dashboard_view_devuelve_403` (403 real, no solo una lista vacía en la UI) |
| La documentación está desactualizada | No | `README.md` actualizado (arquitectura, instalación, variables de entorno, endpoints, seguridad, limitaciones); `docs/integracion/` completo |
| El resultado final se guardó en `skelleton_base` en lugar de `cms_dashboards` | No | Todo el código vive en `C:\Users\itinnouio\ProyectosClaude\cms_dashboards`, rama `feature/integracion-skelleton-base` de este mismo repositorio; `skelleton_base` no se modificó en ningún momento (solo se leyó) |

## Conclusión

Ningún criterio de bloqueo de la sección 31 se cumple hoy, con la excepción explícitamente
justificada de la landing pública (no aplica: nunca existió) y la coexistencia intencional de
dos sistemas de auditoría de dominios distintos. La integración de las Fases 0-9 puede
considerarse completa bajo los criterios definidos; la Fase 10 (esta documentación) cierra el
trabajo de esta ronda. El trabajo diferido queda explícito en `migration_report.md` (sección
"Trabajo futuro"), no oculto.

## Actualización (2026-07-31) — trabajo futuro completado

Las dos excepciones de la conclusión anterior dejaron de ser excepciones:

- **"La landing pública deja de funcionar" — no aplica: nunca existió.** Ahora existe: `/` sirve
  una landing pública completa (Módulo C, ver `docs/public/landing_page.md`).
- **Coexistencia intencional de dos sistemas de auditoría.** Se unificaron en `AuditEvent`
  (Módulo A, ver `docs/audit/unified_audit.md`); `apps.core.AuditLog`/`cartera.DashboardAuditLog`
  se conservan como archivo histórico de solo lectura, no reciben escrituras nuevas.

Además se completaron los otros dos puntos de "Trabajo futuro": integración visual con Bootstrap
(Módulo B) y recuperación de contraseña por correo (Módulo D, incluida una prueba real de envío a
`dpenarreta@grupolaar.com`). Detalle completo en
`docs/integracion/future_work_completion_report.md`. 173 pruebas backend y 207 pruebas frontend
en verde al cierre de esta ronda.

## Cómo reproducir la verificación

```bash
# Backend
cd backend
.venv/Scripts/python.exe manage.py test          # 144/144
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run   # "No changes detected"

# Frontend
cd frontend
npm run test                                      # 164/164
npm run lint                                       # sin errores nuevos
```

Para la verificación manual en navegador: levantar `manage.py runserver 8000` y `npm run dev`,
crear un superusuario (`manage.py createsuperuser`), iniciar sesión, y recorrer `/app/dashboards`,
`/admin/users`, `/admin/roles`, `/admin/permissions`, `/admin/settings`.
