# Pruebas — reglas compartidas

## Comandos

- Backend (todo): `cd backend && python manage.py test`
- Backend (una app): `python manage.py test apps.users` / `python manage.py test cartera`
- Frontend (todo): `cd frontend && npx vitest run` (o `npm test`, mismo comando)
- Frontend (un archivo): `npx vitest run src/tests/NombreDelArchivo.test.jsx`
- Lint frontend: `npm run lint` (oxlint)

## Backend

- IMPORTANT: usa `django.test.TestCase`/`rest_framework.test.APITestCase`. No introduzcas
  `pytest`/`pytest-django` — es una decisión explícita (`docs/integracion/decisions.md`, decisión
  12) para no mantener dos runners de pruebas en el mismo backend.
- Las pruebas corren contra la base configurada en `backend/.env` (`DB_ENGINE`) — con `mssql`
  local, requieren SQL Server real disponible en `DB_HOST:DB_PORT`. No asumas SQLite salvo que
  `DB_ENGINE=sqlite` esté configurado.
- Los correos (`EMAIL_BACKEND`) se fuerzan siempre a `locmem` durante `manage.py test`,
  sin importar el valor en `.env` — no hace falta mockear el envío de correo en pruebas.

## Frontend (Vitest + React Testing Library)

- `frontend/src/tests/setup.js` ya hace polyfill de `IntersectionObserver`, `scrollIntoView` y
  `matchMedia` (jsdom no los implementa). No los vuelvas a definir dentro de un test individual.
- Para mockear `AuthContext` en un componente que llama `useAuth()`:
  `vi.mock('../context/AuthContext', () => ({ useAuth: vi.fn() }))`, y en cada test
  `useAuth.mockReturnValue({ user: {...} })`. Mismo patrón para `ThemeContext`.
- IMPORTANT: la accesibilidad de `getByRole('button', { name })`/`getByRole('link', { name })` se
  computa desde el **texto visible**, no desde el atributo `title`. Si un botón tiene `title="X"`
  pero muestra otro texto visible, consulta por el texto visible.
- `react-bootstrap`'s `Modal.Title` renderiza un `<div>`, no un heading real — no uses
  `getByRole('heading', ...)` para verificarlo, usa `getByText(...)`.
- Componentes que usan `@dnd-kit/core` dentro de un test: envuélvelos en su propio `<DndContext>`
  con `useSensor(PointerSensor, { activationConstraint: { distance: 4 } })` explícito. Un
  `<DndContext>` sin sensores configurados intercepta el `onClick` como inicio de arrastre y lo
  descarta — los clics dejan de disparar el handler.
- No se simula arrastre de puntero real de `dnd-kit` en los tests automatizados del editor visual;
  se cubre la lógica de destino a través del `onClick` de respaldo que dispara el mismo handler
  que un `drop` exitoso (mismo criterio en todo `dashboard-editor`).
