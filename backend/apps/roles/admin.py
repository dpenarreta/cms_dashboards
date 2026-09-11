"""Quita `Group` (los roles del sistema) del admin de Django.

Django lo registra solo, vía `django.contrib.auth.admin`, y desde ahí se editan los permisos de
un rol directamente sobre la tabla: sin pasar por `require_permission('roles.editar')` y sin
escribir un `AuditEvent`. Es el mismo bypass que motivó desregistrar `User` (ver
`apps/users/admin.py`) — cambiar los permisos de un rol es tan sensible como asignarlos a una
persona, porque alcanza a todos sus miembros de una vez.

Los roles se administran por la API (`apps.roles.views.RoleViewSet`) y su pantalla en el frontend
(`/admin/roles`), que validan permiso y auditan cada cambio.

En producción esto es redundante —la ruta `/admin/` no se publica, ver `config/urls.py`— pero en
desarrollo el admin sí está disponible y ahí el bypass era real.
"""

from django.contrib import admin
from django.contrib.auth.models import Group

admin.site.unregister(Group)
