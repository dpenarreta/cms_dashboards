"""Sincroniza las `Meta.permissions` de `ModulePermission` con el catálogo.

`ModulePermission` es un modelo ancla (`managed = False`): no tiene tabla propia, solo existe para
colgarle los permisos del catálogo cerrado (`apps/permissions/catalog.py`). Agregar una entrada
ahí cambia sus `Meta.options`, y Django lo detecta como una migración pendiente aunque no toque
ningún esquema — la creó `makemigrations` al sumarse `dashboard.datos.editar`.

Sin esta migración, `manage.py makemigrations --check` (el paso de CI que verifica que no queden
modelos sin migrar) falla en cada corrida.
"""

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('permissions', '0004_alter_modulepermission_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='modulepermission',
            options={'default_permissions': (), 'managed': False, 'permissions': [('usuarios.ver', 'Ver usuarios'), ('usuarios.crear', 'Crear usuarios'), ('usuarios.editar', 'Editar usuarios y su asignación de roles/permisos'), ('usuarios.deshabilitar', 'Habilitar, deshabilitar, bloquear y desbloquear usuarios'), ('usuarios.restablecer_password', 'Forzar cambio de contraseña o cerrar sesiones activas de un usuario'), ('roles.ver', 'Ver roles y el catálogo de permisos'), ('roles.editar', 'Crear, editar y eliminar roles'), ('permisos.ver', 'Ver el catálogo de permisos y a qué módulo pertenece cada uno'), ('configuracion.ver', 'Ver configuración del sistema'), ('configuracion.editar', 'Editar configuración del sistema'), ('auditoria.ver', 'Ver el registro de auditoría'), ('auditoria.ver_detalle', 'Ver el detalle (valores anteriores y nuevos) de un evento'), ('auditoria.exportar', 'Exportar el registro de auditoría'), ('dashboard.crear', 'Crear nuevos dashboards por área'), ('dashboard.editar', 'Editar el nombre y área de un dashboard'), ('dashboard.eliminar', 'Eliminar un dashboard'), ('dashboard.view', 'Ver Dashboards'), ('dashboard.edit', 'Entrar en modo edición del dashboard'), ('dashboard.layout.edit', 'Editar el diseño (orden/tamaño) del dashboard'), ('dashboard.component.style', 'Editar estilos de un componente del dashboard'), ('dashboard.component.create', 'Crear componentes del dashboard'), ('dashboard.component.delete', 'Eliminar componentes del dashboard'), ('dashboard.configuration.reset', 'Restablecer la configuración del dashboard'), ('dashboard.interpretar', 'Generar la interpretación completa del dashboard con IA'), ('dashboard.hallazgos_ia', 'Generar hallazgos clave por componente con IA'), ('dashboard.fuente_bd.configurar', 'Elegir/cambiar la vista o procedimiento de base de datos, sus parámetros y la frecuencia de actualización automática de un dashboard'), ('dashboard.fuente_bd.actualizar', 'Forzar una actualización inmediata de los datos desde la base de datos ya configurada'), ('dashboard.archivo.cargar', 'Cargar un archivo Excel nuevo que reemplaza los datos de un dashboard ("Cargar otro archivo")'), ('dashboard.datos.editar', 'Procesar, reprocesar, borrar o remapear los datos ya cargados de un dashboard')]},
        ),
    ]
