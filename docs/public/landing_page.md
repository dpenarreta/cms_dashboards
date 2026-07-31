# Landing pública (Módulo C)

Parte de "Trabajo futuro post-integración con skelleton_base" (ver
`docs/integracion/migration_report.md`, sección "Trabajo futuro completado").

## Qué resuelve

Antes de este módulo, `/` redirigía automáticamente a `/app/dashboards/cartera` (o al login si
no había sesión) — no existía ninguna página pública explicando qué es la plataforma. Esto
cerraba además el hueco documentado en
`tests/qa/acceptance-criteria-traceability-skelleton.md` (AC-INT-003/AC-INT-014), que hasta ahora
marcaban "no aplica" por no existir landing.

## Diseño

### Contenido config-driven (sin editor visual — explícitamente no requerido en esta fase)

`frontend/src/config/landingContent.js` separa el texto de cada sección del componente que lo
renderiza: `{id, menuLabel, title, description, isVisible, order, items|steps}`. `LandingPage.jsx`
itera `seccionesVisiblesOrdenadas()` (filtra por `isVisible`, ordena por `order`) — reordenar,
ocultar o cambiar texto de una sección no requiere tocar JSX.

### Secciones

Inicio (hero) → **¿Qué es un CMS?** (definición + 4 conceptos clave, agregada a pedido explícito
del usuario tras el primer despliegue — ver "Rediseño visual" abajo) → Plataforma (9 capacidades,
sección 6.4) → Dashboards (10 tarjetas de área de ejemplo — Gerencia, Finanzas, Operaciones,
Logística, Comercial, Cobranzas, Talento Humano, Tecnología, Servicio al Cliente, Proyectos — cada
una con ícono, descripción, indicadores de ejemplo y una etiqueta "Acceso restringido"; **ninguna
es un enlace**: no autentican ni navegan a un dashboard real, sección 6.5) → Funcionamiento
(diagrama de flujo de 5 nodos: Fuentes empresariales → Vistas autorizadas → Procesamiento → Roles
y permisos → Dashboard, sección 6.6) → Seguridad (7 puntos, sección 6.7) → Beneficios (10 puntos,
sección 6.8) → CTA final ("Accede a los dashboards de tu área") → pie de página (nombre
institucional y logo vía `ThemeContext`, descripción breve, enlaces a cada sección, enlace a
`/login`, enlaces Privacidad/Términos/Contacto, año dinámico `new Date().getFullYear()`, "Todos
los derechos reservados").

**Corrección durante la implementación**: la primera versión de este módulo usaba contenido
inventado (áreas de ejemplo distintas, un flujo de "Cargar/Validar/Procesar/Explorar" en vez del
diagrama de arquitectura de datos pedido, textos de CTA distintos, sin ítem "Inicio" en el menú, un
solo botón en el hero, footer sin descripción/enlaces legales). Se releyó el prompt original
completo (seccion 6, `6.1`-`6.11`) y se corrigió el contenido para que coincida con lo
explícitamente pedido — solo el título/descripción del hero está marcado como "sugerido" en el
prompt; el resto de las listas (áreas, capacidades de la sección Plataforma, puntos de Seguridad/
Beneficios, textos del CTA) son contenido dado directamente, no una sugerencia.

### Hero

Mockup de dashboard en CSS/HTML puro (`HeroMockup`, sin imágenes de stock): tarjetas KPI con
degradado, gráfico de barras, donut (`conic-gradient`), filas de tabla — todo con las variables
institucionales (`--color-primary`, `--series-*`) ya definidas en `dashboard.css`.

### `PublicNavbar.jsx`

Sticky (`position: sticky; top: 0`), resalta la sección activa con `IntersectionObserver`
(`rootMargin: '-40% 0px -50% 0px'` — considera "activa" la sección que ocupa la franja central de
la pantalla), scroll suave (`scrollIntoView({behavior:'smooth'})`), hamburguesa en móvil
(`aria-expanded`, se cierra al seleccionar una sección).

**Bug encontrado y corregido durante la verificación manual**: al hacer clic en un enlace del
menú, la sección de destino quedaba con su título tapado por el propio navbar sticky (el navegador
alinea el borde superior de la sección exactamente con `y=0`, que es donde está el navbar). Se
corrigió con `scroll-margin-top: 76px` en `#inicio`/`.landing-section` — verificado visualmente
en Chrome que el título de cada sección queda completamente visible debajo del menú.

**Segundo bug encontrado y corregido**: `.landing-page` tenía `overflow-x: hidden` como red de
seguridad contra desbordamiento horizontal. Esto rompió el `position: sticky` del navbar (crea un
nuevo contexto de scroll) — se verificó visualmente que el menú dejaba de pegarse arriba al hacer
scroll. Se quitó esa regla; el diseño responsivo (grids con `minmax`, `flex-wrap`, breakpoint a
860px) es lo que evita el desbordamiento, no un recorte posterior.

### Ruta

`/` deja de redirigir y renderiza `LandingPage` (pública, fuera de `AuthenticatedLayout`, sin
`RequirePermission`) — accesible sin sesión. El destino post-login no cambia: sigue siendo
`/app/dashboards/cartera` (`LoginPage.jsx`, sin modificar).

### Rediseño visual (a pedido del usuario, posterior al primer despliegue)

El usuario compartió dos referencias visuales: un hero de tipo "CMS" (encabezado oscuro con
navegación, título grande, ilustración con íconos conectados por líneas punteadas) y una landing
completa de estilo "Lumosity" (secciones alternadas de fondo claro/oscuro, grids de íconos de
color, banda de características con captura de pantalla, franja de llamado a la acción en un
color de acento). Ninguna de las dos imágenes se reprodujo ni se copió (son ilustraciones de stock
con derechos de autor) — se reconstruyó la **composición** con CSS/HTML propio y emoji, igual que
el mockup de dashboard ya existente:

- **Navbar**: pasa de blanco a un azul marino fijo (`--landing-navy`, decorativo, no
  institucional) con texto claro — mismo componente y misma lógica de scroll-spy/scroll suave/
  hamburguesa de antes, sin cambios de comportamiento.
- **Hero**: fondo con degradado oscuro y una franja diagonal sutil (`::before` con
  `linear-gradient`), título grande ("CMS Dashboards"), subtítulo corto en mayúsculas ("Sistema de
  gestión de contenido para dashboards"), párrafo descriptivo, y **dos** botones (antes uno):
  `Probar ahora` (`btn-primary`, ancla a `#que-es-un-cms`) e `Ingresar` (`btn-outline-light`).
  Alrededor del mockup del dashboard se agregaron 6 nodos circulares con íconos (🛒☁️🔧🖼️📄🪛)
  posicionados de forma absoluta y conectados visualmente por un recuadro punteado — inspirado en
  la composición de la referencia, sin copiar su arte.
- **Nueva sección "¿Qué es un CMS?"**: pedida explícitamente por el usuario ("incluye lo que es un
  CMS, cómo funciona"). Definición breve + 4 tarjetas con ícono circular de color
  (`icon-circle` + `bg-{color}`, reutilizando las clases de Bootstrap ya conectadas a los colores
  institucionales por el Módulo B — no una paleta nueva).
- **Plataforma/Beneficios**: pasan de tarjetas blancas lisas a un grid de íconos circulares de
  colores (mismo patrón `icon-circle`/`bg-{color}`), replicando el estilo "what you'll get" de la
  referencia.
- **Seguridad**: pasa de tarjetas a una lista de verificación (`checklist`) con ícono + texto en
  dos columnas.
- **Funcionamiento**: se envuelve en una "banda de características" (`feature-band`, fondo oscuro)
  con el diagrama de flujo a la izquierda y una copia compacta del mockup de dashboard a la
  derecha — replicando la banda de captura de pantalla de la referencia.
- **CTA final**: cambia de `var(--color-primary)` a `var(--color-secondary)` para dar contraste de
  color respecto al resto de la página (la referencia usa un acento naranja distinto del color
  principal).

Ningún cambio de comportamiento (rutas, permisos, scroll-spy, IDs de sección) — solo presentación.
Se actualizaron las pruebas afectadas (aserciones sobre las dos CTA del hero) y se verificó
visualmente en Chrome cada sección tras el cambio, confirmando que el navbar sigue sin taparse
las secciones (mismo `scroll-margin-top` ya corregido antes) y que no hay errores de consola.

## Pruebas

- `frontend/src/tests/landingContent.test.js` — config-driven (orden, visibilidad, sin enlaces
  reales en "Dashboards").
- `frontend/src/tests/PublicNavbar.test.jsx` — enlaces por sección, marca institucional, botón
  "Ingresar", toggle móvil (`aria-expanded`).
- `frontend/src/tests/LandingPage.test.jsx` — hero, 5 secciones, 10 áreas de ejemplo sin enlaces,
  pie de página con año dinámico y enlace a `/login`.
- jsdom no implementa `IntersectionObserver`/`scrollIntoView`: se agregaron stubs mínimos en
  `frontend/src/tests/setup.js` (mismo patrón ya usado para `matchMedia`).
- Verificación manual en Chrome: landing completa sin sesión, scroll a cada sección (navbar
  pegado, título no tapado), sin errores de consola.
