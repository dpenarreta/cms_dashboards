"""Lógica de administración de usuarios (creación, edición, estado, roles/permisos).

Las validaciones de negocio lanzan `cartera.exceptions.CarteraError` para que toda la API
responda con el mismo contrato de error (`docs/integracion/decisions.md` #7), en vez de
introducir un segundo shape de error propio de esta app.
"""

import secrets

from django.contrib.auth.models import Group, Permission
from django.db import transaction

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.authentication.services import SessionService
from cartera.exceptions import CarteraError

from .models import User

# Sin caracteres ambiguos (l/I/1, O/0) para que una contraseña temporal leída/tipeada a mano no
# genere confusión; mezcla de mayúsculas/minúsculas/dígitos por construcción, para satisfacer
# `NumericPasswordValidator` sin tener que invocar los validadores manualmente.
_ALFABETO_PASSWORD_TEMPORAL = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def _generar_password_temporal(longitud=12):
    return ''.join(secrets.choice(_ALFABETO_PASSWORD_TEMPORAL) for _ in range(longitud))


def _es_ultimo_administrador_activo(usuario):
    if not usuario.is_superuser:
        return False
    otros_admins_activos = User.objects.filter(
        is_superuser=True, status=User.Status.ACTIVE,
    ).exclude(pk=usuario.pk).exists()
    return not otros_admins_activos


class UserAdminService:
    @staticmethod
    @transaction.atomic
    def create_user(*, data, created_by=None):
        password = data.pop('password')
        usuario = User(**data, created_by=created_by)
        usuario.set_password(password)
        usuario.save()
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_CREATED', actor=created_by,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            new_values={'username': usuario.username, 'email': usuario.email},
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def update_user(*, usuario, data, updated_by=None):
        anterior = {'email': usuario.email, 'first_name': usuario.first_name, 'last_name': usuario.last_name}
        for campo, valor in data.items():
            setattr(usuario, campo, valor)
        usuario.updated_by = updated_by
        usuario.save()
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_UPDATED', actor=updated_by,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            previous_values=anterior, new_values=data,
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def _set_status(*, usuario, status, actor=None, action=''):
        if status != User.Status.ACTIVE and _es_ultimo_administrador_activo(usuario):
            raise CarteraError(
                'No se puede deshabilitar/bloquear al último administrador general activo.',
                codigo='ULTIMO_ADMINISTRADOR_ACTIVO',
            )
        usuario.status = status
        usuario.updated_by = actor
        usuario.save()
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action=action, actor=actor,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
        )
        return usuario

    @staticmethod
    def enable(*, usuario, actor=None):
        return UserAdminService._set_status(usuario=usuario, status=User.Status.ACTIVE, actor=actor, action='USER_ENABLED')

    @staticmethod
    def disable(*, usuario, actor=None):
        return UserAdminService._set_status(usuario=usuario, status=User.Status.DISABLED, actor=actor, action='USER_DISABLED')

    @staticmethod
    def block(*, usuario, actor=None):
        return UserAdminService._set_status(usuario=usuario, status=User.Status.BLOCKED, actor=actor, action='USER_BLOCKED')

    @staticmethod
    def unblock(*, usuario, actor=None):
        return UserAdminService._set_status(usuario=usuario, status=User.Status.ACTIVE, actor=actor, action='USER_UNBLOCKED')

    @staticmethod
    @transaction.atomic
    def assign_roles(*, usuario, role_ids, actor=None):
        roles = list(Group.objects.filter(pk__in=[r.pk for r in role_ids]))
        usuario.groups.set(roles)
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_ROLES_ASSIGNED', actor=actor,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            new_values={'roles': [r.name for r in roles]},
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def set_superuser(*, usuario, es_superusuario, actor=None):
        """Otorga o quita el estado de superusuario (`is_superuser`) — solo lo puede invocar otro
        superusuario (`apps.permissions.permissions.IsSuperuser`, no un permiso del catálogo de
        negocio). No se puede quitar al último superusuario activo, igual que no se puede
        deshabilitar/bloquear (`_es_ultimo_administrador_activo`) — sin este resguardo, el sistema
        podría quedar sin ninguna cuenta capaz de volver a otorgar superusuario."""
        if not es_superusuario and usuario.is_superuser and _es_ultimo_administrador_activo(usuario):
            raise CarteraError(
                'No se puede quitar el estado de superusuario al último superusuario activo.',
                codigo='ULTIMO_ADMINISTRADOR_ACTIVO',
            )
        anterior = usuario.is_superuser
        usuario.is_superuser = es_superusuario
        usuario.updated_by = actor
        usuario.save()
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_SUPERUSER_CHANGED', actor=actor,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            previous_values={'is_superuser': anterior}, new_values={'is_superuser': es_superusuario},
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def reset_password(*, usuario, actor=None):
        """Genera una contraseña temporal aleatoria y la aplica de inmediato, fuerza el cambio en
        el próximo login (`must_change_password`) y revoca todas las sesiones activas del usuario
        — mismo efecto final que `PasswordResetService.confirmar` (recuperación por correo), pero
        iniciado por un admin y sin depender de que el usuario tenga acceso a su correo. La
        contraseña en texto plano solo existe en el valor de retorno: no se guarda en ningún lado,
        así que hay que devolverla al llamador ahora, es la única oportunidad."""
        password_temporal = _generar_password_temporal()
        usuario.set_password(password_temporal)
        usuario.must_change_password = True
        usuario.updated_by = actor
        usuario.save()
        SessionService.revocar_todas(usuario)
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_PASSWORD_RESET_BY_ADMIN', actor=actor,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
        )
        return usuario, password_temporal

    @staticmethod
    @transaction.atomic
    def assign_permissions(*, usuario, codenames, actor=None):
        # Los codenames de negocio (ej. "usuarios.ver") son el `codename` real del `Permission`
        # (ver apps/permissions/models.py); el prefijo "permissions." solo aplica al string que
        # usa `has_perm`, no al campo `codename` almacenado en `auth_permission`.
        permisos = list(Permission.objects.filter(codename__in=codenames, content_type__app_label='permissions'))
        usuario.user_permissions.set(permisos)
        log_event(
            domain=AuditEvent.Domain.PERMISSION_MANAGEMENT, action='USER_PERMISSIONS_ASSIGNED', actor=actor,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            new_values={'permissions': codenames},
        )
        return usuario
