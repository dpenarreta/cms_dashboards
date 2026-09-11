"""`User` NO se registra en el admin de Django, a propósito.

`DjangoUserAdmin` permite editar `is_superuser`, grupos y permisos directamente sobre la tabla,
sin pasar por `apps.permissions.permissions.IsSuperuser` (que existe justamente para que ni un
permiso asignable del catálogo alcance para conceder superusuario) y sin escribir un solo
`AuditEvent`. Es decir que era un segundo camino, paralelo y sin auditoría, para exactamente la
operación más sensible del sistema.

La administración de usuarios se hace por la API (`apps.users.views.UserAdminViewSet`) y su
pantalla en el frontend (`/admin/users`), que sí validan permisos y auditan cada cambio. Si hace
falta una consulta puntual sobre la tabla, `python manage.py shell` deja el mismo rastro (ninguno)
pero exige acceso al servidor, no una contraseña por HTTP.
"""
