/**
 * Contenido de la landing pública: texto separado de los componentes que lo renderizan, para que
 * editar una sección no implique tocar JSX. No es un editor visual completo (explícitamente no
 * requerido en esta fase) — es la estructura mínima config-driven que permite reordenar/ocultar
 * secciones y cambiar texto en un solo lugar.
 */

export const HERO_CONTENT = {
  eyebrow: 'Plataforma de dashboards institucionales',
  title: 'CMS Dashboards',
  subtitle: 'Sistema de gestión de contenido para dashboards',
  description:
    'Centraliza la carga, configuración y visualización de indicadores institucionales en un '
    + 'solo lugar — seguro, configurable y adaptado a cada área, sin depender de escribir código '
    + 'para cada cambio.',
  primaryCtaLabel: 'Probar ahora',
  primaryCtaHref: '#que-es-un-cms',
  secondaryCtaLabel: 'Ingresar',
  secondaryCtaHref: '/login',
}

export const QUE_ES_CONTENT = {
  id: 'que-es-un-cms',
  menuLabel: 'Qué es',
  order: 1,
  isVisible: true,
  title: '¿Qué es un CMS?',
  description:
    'Un CMS (Content/Component Management System) es un sistema que centraliza la gestión de '
    + 'contenido, configuración y visualización de información — en este caso, dashboards '
    + 'institucionales — sin depender de escribir código para cada cambio.',
  items: [
    { icon: '🗂️', color: 'primary', title: 'Gestión centralizada', description: 'Todo el contenido y la configuración institucional en un solo lugar.' },
    { icon: '🧩', color: 'success', title: 'Sin código', description: 'Colores, textos y estructura se ajustan desde una pantalla de administración.' },
    { icon: '🔐', color: 'info', title: 'Roles y permisos', description: 'Cada usuario ve y edita solo lo que su rol le habilita.' },
    { icon: '⚡', color: 'warning', title: 'Actualización en tiempo real', description: 'Los cambios se reflejan de inmediato, sin desplegar código nuevo.' },
  ],
}

export const LANDING_SECTIONS = [
  {
    id: 'inicio',
    menuLabel: 'Inicio',
    order: 0,
    isVisible: true,
  },
  QUE_ES_CONTENT,
  {
    id: 'plataforma',
    menuLabel: 'Plataforma',
    order: 2,
    isVisible: true,
    title: 'Una sola plataforma para toda la organización',
    description: 'CMS Dashboards permite:',
    items: [
      { icon: '📊', color: 'primary', title: 'Centralizar dashboards', description: 'Todos los indicadores de la organización en un solo lugar.' },
      { icon: '📉', color: 'secondary', title: 'Reducir reportes manuales', description: 'Menos hojas de cálculo dispersas y reportes armados a mano.' },
      { icon: '✅', color: 'success', title: 'Consultar información confiable', description: 'Datos validados antes de mostrarse en cualquier panel.' },
      { icon: '🔍', color: 'info', title: 'Aplicar filtros', description: 'Explora cada dashboard por los criterios que necesites.' },
      { icon: '⬇️', color: 'warning', title: 'Exportar datos autorizados', description: 'Descarga solo la información que tu rol permite.' },
      { icon: '🎨', color: 'danger', title: 'Personalizar componentes', description: 'Orden, tamaño y estilo de cada panel, sin tocar código.' },
      { icon: '🗃️', color: 'primary', title: 'Organizar dashboards', description: 'Cada área tiene su propio espacio dentro de la plataforma.' },
      { icon: '🔗', color: 'success', title: 'Conectar vistas de base de datos', description: 'Los dashboards consultan vistas controladas, no datos crudos.' },
      { icon: '🛡️', color: 'info', title: 'Controlar accesos mediante roles y permisos', description: 'Cada usuario ve solo lo que su rol le habilita.' },
    ],
  },
  {
    id: 'dashboards',
    menuLabel: 'Dashboards',
    order: 3,
    isVisible: true,
    title: 'Dashboards para cada área de la organización',
    description: 'Ejemplos de áreas que la plataforma puede cubrir:',
    // Ilustrativas: no enlazan a dashboards reales ni requieren sesión (sección 6.5: "las
    // tarjetas no deben acceder a dashboards sin autenticación").
    items: [
      { title: 'Gerencia', icon: '🏢', description: 'Visión general del desempeño institucional.', indicadores: ['Cumplimiento de metas', 'Rentabilidad'] },
      { title: 'Finanzas', icon: '💰', description: 'Flujo de caja y proyecciones financieras.', indicadores: ['Flujo de caja', 'Margen'] },
      { title: 'Operaciones', icon: '⚙️', description: 'Eficiencia y cumplimiento de procesos.', indicadores: ['Eficiencia', 'Tiempos de ciclo'] },
      { title: 'Logística', icon: '🚚', description: 'Cumplimiento de entregas y rutas.', indicadores: ['Entregas a tiempo', 'Costo por ruta'] },
      { title: 'Comercial', icon: '📈', description: 'Desempeño de ventas por período y canal.', indicadores: ['Ventas', 'Conversión'] },
      { title: 'Cobranzas', icon: '💳', description: 'Gestión y efectividad de recuperadores.', indicadores: ['Cartera vencida', 'Recuperación'] },
      { title: 'Talento Humano', icon: '👥', description: 'Dotación, ausentismo y rotación de personal.', indicadores: ['Rotación', 'Ausentismo'] },
      { title: 'Tecnología', icon: '💻', description: 'Disponibilidad e incidentes de los sistemas.', indicadores: ['Disponibilidad', 'Incidentes'] },
      { title: 'Servicio al Cliente', icon: '🎧', description: 'Volumen y tiempos de resolución de casos.', indicadores: ['Tiempo de resolución', 'Satisfacción'] },
      { title: 'Proyectos', icon: '📋', description: 'Avance y cumplimiento de proyectos activos.', indicadores: ['Avance', 'Cumplimiento'] },
    ],
  },
  {
    id: 'funcionamiento',
    menuLabel: 'Funcionamiento',
    order: 4,
    isVisible: true,
    title: 'Cómo funciona',
    description: 'De la fuente de datos al dashboard que ve cada usuario:',
    steps: [
      { title: 'Fuentes empresariales', description: 'La información se obtiene de fuentes autorizadas.' },
      { title: 'Vistas autorizadas', description: 'Cada dashboard consulta vistas controladas, no datos crudos.' },
      { title: 'Procesamiento', description: 'Los datos se transforman en KPI y gráficos.' },
      { title: 'Roles y permisos', description: 'Los permisos determinan qué puede ver cada usuario.' },
      { title: 'Dashboard', description: 'El usuario visualiza únicamente la información autorizada.' },
    ],
  },
  {
    id: 'seguridad',
    menuLabel: 'Seguridad',
    order: 5,
    isVisible: true,
    title: 'Seguridad de extremo a extremo',
    description: '',
    items: [
      { icon: '🔑', title: 'Inicio de sesión seguro', description: 'Autenticación JWT con sesiones revocables.' },
      { icon: '🔒', title: 'Contraseñas protegidas', description: 'Almacenadas siempre mediante hash, nunca en texto plano.' },
      { icon: '🧑‍💼', title: 'Roles y permisos', description: 'Cada acción sensible exige un permiso concreto, verificado en el servidor.' },
      { icon: '🚧', title: 'Protección de rutas', description: 'Acceso restringido por dashboard según el perfil del usuario.' },
      { icon: '🕵️', title: 'Auditoría unificada', description: 'Registro de accesos y cambios, consultable por un administrador.' },
      { icon: '✉️', title: 'Recuperación segura de contraseña', description: 'Enlaces de un solo uso, con expiración, enviados por correo.' },
      { icon: '🗄️', title: 'Fuentes de datos controladas', description: 'La información se consulta desde vistas autorizadas, no directamente.' },
    ],
  },
  {
    id: 'beneficios',
    menuLabel: 'Beneficios',
    order: 6,
    isVisible: true,
    title: 'Lo que vas a obtener',
    description: '',
    items: [
      { icon: '🗂️', color: 'primary', title: 'Una sola plataforma', description: 'Todos los dashboards de la organización en un mismo lugar.' },
      { icon: '📉', color: 'secondary', title: 'Menos archivos dispersos', description: 'Sin hojas de cálculo repetidas por cada área.' },
      { icon: '🔄', color: 'success', title: 'Información actualizada', description: 'Los indicadores reflejan siempre el dato más reciente cargado.' },
      { icon: '🎯', color: 'info', title: 'Mejor toma de decisiones', description: 'Datos confiables, listos para consultar.' },
      { icon: '🤖', color: 'warning', title: 'Menor dependencia de reportes manuales', description: 'Los KPI se calculan automáticamente.' },
      { icon: '🛡️', color: 'danger', title: 'Acceso controlado', description: 'Cada usuario ve solo lo que su rol permite.' },
      { icon: '🕵️', color: 'primary', title: 'Auditoría', description: 'Trazabilidad de accesos y cambios de configuración.' },
      { icon: '🎨', color: 'success', title: 'Configuración visual', description: 'Identidad institucional propia, sin depender de desarrollo.' },
      { icon: '📈', color: 'info', title: 'Escalabilidad', description: 'Pensada para sumar nuevas áreas sin rediseñar el sistema.' },
      { icon: '📐', color: 'warning', title: 'Estandarización', description: 'Un mismo criterio de calidad de datos para toda la organización.' },
    ],
  },
]

export const CTA_CONTENT = {
  title: 'Accede a los dashboards de tu área',
  subtitle: 'Inicia sesión para consultar la información disponible según tu perfil y permisos.',
  ctaLabel: 'Ingresar a la plataforma',
  ctaHref: '/login',
}

export const FOOTER_CONTENT = {
  description: 'Dashboards institucionales seguros, configurables y adaptados a cada área.',
  legalLinks: [
    { label: 'Privacidad', href: '#' },
    { label: 'Términos', href: '#' },
    { label: 'Contacto', href: 'mailto:soporte@example.com' },
  ],
}

export function seccionesVisiblesOrdenadas() {
  return LANDING_SECTIONS.filter((s) => s.isVisible).sort((a, b) => a.order - b.order)
}

/** Secciones con contenido de sección (todas menos "Inicio", que es solo una entrada de menú
 * hacia el hero, sin bloque propio). */
export function seccionesDeContenido() {
  return seccionesVisiblesOrdenadas().filter((s) => s.id !== 'inicio')
}
