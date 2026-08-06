# services/

Hereda `../../CLAUDE.md`. Un archivo de servicio por dominio de API — sin lógica de UI ni de
React acá, solo llamadas HTTP y el `.then((r) => r.data)`.

## Wrappers Axios (por qué son tres, no uno)

Los tres se construyen con el mismo factory `httpClient.js::createApiClient(baseURL)` (interceptor
de Bearer token + refresh automático en 401 ya incluido) — difieren solo en el prefijo:

| Wrapper | `baseURL` | Usado por |
|---|---|---|
| `authApi` (`authApi.js`) | `/api` | `authService`, `usersService`, `rolesService`, `permissionsService`, `brandingService`, `auditService` |
| `api` (`api.js`) | `/api/cartera` | `carteraService`, `plantillaBaseService`, `historicoService` |
| instancia inline en `dashboardLayoutService.js` | `/api/dashboards` | solo ese archivo |

Un servicio nuevo: si pega contra `/api/cartera/*`, reexporta `api` de `api.js`; si pega contra
otro prefijo nuevo de backend, créalo con `createApiClient('/api/tu-prefijo')`, no reuses `api` ni
`authApi` con una ruta que no corresponda a su prefijo.

## Manejo de errores

Ningún servicio atrapa errores — deja que la promesa rechace y que el hook/página que lo llama
decida el mensaje (`e.response?.data?.mensaje`). No agregues `.catch()` dentro de un servicio.

## Archivos (14) — una línea por cubrimiento

`httpClient.js` (factory + interceptores), `api.js`/`authApi.js` (instancias), `authService.js`
(auth), `usersService.js`, `rolesService.js`, `permissionsService.js`, `brandingService.js`,
`auditService.js`, `carteraService.js` (validación/mapeo/KPIs/exportar de cartera legado),
`dashboardLayoutService.js` (layout/versions/pestañas/acceso de dashboards reales),
`historicoService.js`, `plantillaBaseService.js`.

## Evita

- No leas ni ramifiques por el campo `error` (código) del contrato de error del backend — hoy
  ningún servicio ni página lo usa, solo `mensaje`. Si necesitas manejo por código de error,
  confírmalo primero: sería el primer lugar que lo hace.
