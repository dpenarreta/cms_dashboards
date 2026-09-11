"""Catálogo cerrado de permisos del sistema (única fuente de verdad).

Incluye los permisos administrativos de skelleton_base (usuarios/roles/permisos/configuración/
auditoría) y los 7 permisos ya existentes de `cartera.permisos` (sin renombrarlos, para no tocar
sus call-sites). Agregar un permiso nuevo aquí lo hace disponible automáticamente para asignar a
cualquier rol, incluido `ADMINISTRADOR_GENERAL` (que se siembra con el catálogo completo).
"""

PERMISSION_CATALOG = [
    # --- Usuarios ---------------------------------------------------------------
    {'module': 'usuarios', 'codename': 'usuarios.ver', 'name': 'Ver usuarios'},
    {'module': 'usuarios', 'codename': 'usuarios.crear', 'name': 'Crear usuarios'},
    {'module': 'usuarios', 'codename': 'usuarios.editar', 'name': 'Editar usuarios y su asignación de roles/permisos'},
    {'module': 'usuarios', 'codename': 'usuarios.deshabilitar', 'name': 'Habilitar, deshabilitar, bloquear y desbloquear usuarios'},
    {'module': 'usuarios', 'codename': 'usuarios.restablecer_password', 'name': 'Forzar cambio de contraseña o cerrar sesiones activas de un usuario'},
    # --- Roles --------------------------------------------------------------------
    {'module': 'roles', 'codename': 'roles.ver', 'name': 'Ver roles y el catálogo de permisos'},
    {'module': 'roles', 'codename': 'roles.editar', 'name': 'Crear, editar y eliminar roles'},
    # --- Permisos -------------------------------------------------------------------
    {'module': 'permisos', 'codename': 'permisos.ver', 'name': 'Ver el catálogo de permisos y a qué módulo pertenece cada uno'},
    # --- Configuración institucional --------------------------------------------------
    {'module': 'configuracion', 'codename': 'configuracion.ver', 'name': 'Ver configuración del sistema'},
    {'module': 'configuracion', 'codename': 'configuracion.editar', 'name': 'Editar configuración del sistema'},
    # --- Auditoría -------------------------------------------------------------------
    {'module': 'auditoria', 'codename': 'auditoria.ver', 'name': 'Ver el registro de auditoría'},
    {'module': 'auditoria', 'codename': 'auditoria.ver_detalle', 'name': 'Ver el detalle (valores anteriores y nuevos) de un evento'},
    {'module': 'auditoria', 'codename': 'auditoria.exportar', 'name': 'Exportar el registro de auditoría'},
    # --- Dashboard de cartera (ya existentes en cartera.permisos, sin renombrar) ------
    {'module': 'dashboard', 'codename': 'dashboard.crear', 'name': 'Crear nuevos dashboards por área'},
    {'module': 'dashboard', 'codename': 'dashboard.editar', 'name': 'Editar el nombre y área de un dashboard'},
    {'module': 'dashboard', 'codename': 'dashboard.eliminar', 'name': 'Eliminar un dashboard'},
    {'module': 'dashboard', 'codename': 'dashboard.view', 'name': 'Ver Dashboards'},
    {'module': 'dashboard', 'codename': 'dashboard.edit', 'name': 'Entrar en modo edición del dashboard'},
    {'module': 'dashboard', 'codename': 'dashboard.layout.edit', 'name': 'Editar el diseño (orden/tamaño) del dashboard'},
    {'module': 'dashboard', 'codename': 'dashboard.component.style', 'name': 'Editar estilos de un componente del dashboard'},
    {'module': 'dashboard', 'codename': 'dashboard.component.create', 'name': 'Crear componentes del dashboard'},
    {'module': 'dashboard', 'codename': 'dashboard.component.delete', 'name': 'Eliminar componentes del dashboard'},
    {'module': 'dashboard', 'codename': 'dashboard.configuration.reset', 'name': 'Restablecer la configuración del dashboard'},
    # --- Interpretación con IA (Gemini) — separados de dashboard.view para poder controlar el
    # costo/uso del LLM sin depender de quién puede simplemente ver el dashboard -------------
    {'module': 'dashboard', 'codename': 'dashboard.interpretar', 'name': 'Generar la interpretación completa del dashboard con IA'},
    {'module': 'dashboard', 'codename': 'dashboard.hallazgos_ia', 'name': 'Generar hallazgos clave por componente con IA'},
    # --- Conexión a base de datos externa — separados de dashboard.editar/dashboard.view porque
    # exponen la conexión a la base de datos productiva configurada por el sistema, no un permiso
    # genérico de "editar contenido del dashboard" -----------------------------------------------
    {'module': 'dashboard', 'codename': 'dashboard.fuente_bd.configurar', 'name': 'Elegir/cambiar la vista o procedimiento de base de datos, sus parámetros y la frecuencia de actualización automática de un dashboard'},
    {'module': 'dashboard', 'codename': 'dashboard.fuente_bd.actualizar', 'name': 'Forzar una actualización inmediata de los datos desde la base de datos ya configurada'},
    # --- Carga de archivo Excel — separado de dashboard.view: antes "quien puede ver, puede
    # cargar", ahora es un permiso propio, igual criterio que dashboard.fuente_bd.configurar -----
    {'module': 'dashboard', 'codename': 'dashboard.archivo.cargar', 'name': 'Cargar un archivo Excel nuevo que reemplaza los datos de un dashboard ("Cargar otro archivo")'},
    # --- Mutación de los datos ya cargados — separado de dashboard.view, mismo criterio que
    # dashboard.archivo.cargar y dashboard.fuente_bd.configurar. Antes estas acciones caían al
    # genérico "quien puede ver el dashboard puede mutar sus datos", así que cualquiera con
    # `dashboard.view` podía BORRAR la carga completa de un dashboard sin ACL propia -------------
    {'module': 'dashboard', 'codename': 'dashboard.datos.editar', 'name': 'Procesar, reprocesar, borrar o remapear los datos ya cargados de un dashboard'},
]


def as_django_permission_tuples():
    return [(p['codename'], p['name']) for p in PERMISSION_CATALOG]


def modules():
    vistos = []
    for p in PERMISSION_CATALOG:
        if p['module'] not in vistos:
            vistos.append(p['module'])
    return vistos
