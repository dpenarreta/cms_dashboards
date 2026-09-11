"""Lógica de administración de usuarios (creación, edición, estado, roles/permisos).

Las validaciones de negocio lanzan `cartera.exceptions.CarteraError` para que toda la API
responda con el mismo contrato de error (`docs/integracion/decisions.md` #7), en vez de
introducir un segundo shape de error propio de esta app.
"""

import secrets

from django.contrib.auth.models import Group, Permission
from django.db import transaction
from rest_framework.exceptions import ValidationError as DRFValidationError

from apps.audit.models import AuditEvent
from apps.audit.services import log_event
from apps.authentication.services import SessionService
from apps.core.password import validar_fortaleza
from cartera.exceptions import CarteraError

from .models import User

# Sin caracteres ambiguos (l/I/1, O/0) para que una contraseña temporal leída/tipeada a mano no
# genere confusión; mezcla de mayúsculas/minúsculas/dígitos por construcción, para satisfacer
# `NumericPasswordValidator` sin tener que invocar los validadores manualmente.
_ALFABETO_PASSWORD_TEMPORAL = 'abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789'


def _generar_password_temporal(longitud=12, usuario=None):
    """Genera una contraseña temporal que además pasa `AUTH_PASSWORD_VALIDATORS`.

    La mezcla del alfabeto ya hace improbable que un sorteo caiga en algo que los validadores
    rechacen, pero "improbable" no es "imposible" (y dejaría de valer si alguien cambia el
    alfabeto), así que se verifica y se vuelve a sortear. Importa porque el usuario tiene que
    poder iniciar sesión con esta contraseña: si no cumpliera las mismas reglas que ahora se
    exigen al cambiarla, el reset entregaría una credencial que el propio sistema rechaza.
    """
    for _ in range(10):
        candidata = ''.join(secrets.choice(_ALFABETO_PASSWORD_TEMPORAL) for _ in range(longitud))
        try:
            validar_fortaleza(candidata, usuario)
        except DRFValidationError:
            continue
        return candidata
    # 10 sorteos rechazados significa que el alfabeto o los validadores quedaron incompatibles —
    # es un error de configuración, no algo a resolver en silencio con una contraseña débil.
    raise CarteraError(
        'No se pudo generar una contraseña temporal que cumpla las reglas configuradas.',
        codigo='PASSWORD_TEMPORAL_NO_GENERADA',
    )


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
    def create_user(*, data, created_by=None, request=None):
        password = data.pop('password')
        usuario = User(**data, created_by=created_by)
        usuario.set_password(password)
        usuario.save()
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_CREATED', actor=created_by,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            new_values={'username': usuario.username, 'email': usuario.email},
            request=request,
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def update_user(*, usuario, data, updated_by=None, request=None):
        anterior = {'email': usuario.email, 'first_name': usuario.first_name, 'last_name': usuario.last_name}
        for campo, valor in data.items():
            setattr(usuario, campo, valor)
        usuario.updated_by = updated_by
        usuario.save()
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_UPDATED', actor=updated_by,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            previous_values=anterior, new_values=data,
            request=request,
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def _set_status(*, usuario, status, actor=None, action='', request=None):
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
            request=request,
        )
        return usuario

    @staticmethod
    def enable(*, usuario, actor=None, request=None):
        return UserAdminService._set_status(usuario=usuario, status=User.Status.ACTIVE, actor=actor, action='USER_ENABLED', request=request)

    @staticmethod
    def disable(*, usuario, actor=None, request=None):
        return UserAdminService._set_status(usuario=usuario, status=User.Status.DISABLED, actor=actor, action='USER_DISABLED', request=request)

    @staticmethod
    def block(*, usuario, actor=None, request=None):
        return UserAdminService._set_status(usuario=usuario, status=User.Status.BLOCKED, actor=actor, action='USER_BLOCKED', request=request)

    @staticmethod
    def unblock(*, usuario, actor=None, request=None):
        return UserAdminService._set_status(usuario=usuario, status=User.Status.ACTIVE, actor=actor, action='USER_UNBLOCKED', request=request)

    @staticmethod
    @transaction.atomic
    def assign_roles(*, usuario, role_ids, actor=None, request=None):
        roles = list(Group.objects.filter(pk__in=[r.pk for r in role_ids]))
        usuario.groups.set(roles)
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_ROLES_ASSIGNED', actor=actor,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            new_values={'roles': [r.name for r in roles]},
            request=request,
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def set_superuser(*, usuario, es_superusuario, actor=None, request=None):
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
            request=request,
        )
        return usuario

    @staticmethod
    @transaction.atomic
    def reset_password(*, usuario, actor=None, request=None):
        """Genera una contraseña temporal aleatoria y la aplica de inmediato, fuerza el cambio en
        el próximo login (`must_change_password`) y revoca todas las sesiones activas del usuario
        — mismo efecto final que `PasswordResetService.confirmar` (recuperación por correo), pero
        iniciado por un admin y sin depender de que el usuario tenga acceso a su correo. La
        contraseña en texto plano solo existe en el valor de retorno: no se guarda en ningún lado,
        así que hay que devolverla al llamador ahora, es la única oportunidad."""
        password_temporal = _generar_password_temporal(usuario=usuario)
        usuario.set_password(password_temporal)
        usuario.must_change_password = True
        usuario.updated_by = actor
        usuario.save()
        SessionService.revocar_todas(usuario)
        log_event(
            domain=AuditEvent.Domain.USER_MANAGEMENT, action='USER_PASSWORD_RESET_BY_ADMIN', actor=actor,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            request=request,
        )
        return usuario, password_temporal

    @staticmethod
    @transaction.atomic
    def assign_permissions(*, usuario, codenames, actor=None, request=None):
        # Los codenames de negocio (ej. "usuarios.ver") son el `codename` real del `Permission`
        # (ver apps/permissions/models.py); el prefijo "permissions." solo aplica al string que
        # usa `has_perm`, no al campo `codename` almacenado en `auth_permission`.
        permisos = list(Permission.objects.filter(codename__in=codenames, content_type__app_label='permissions'))
        usuario.user_permissions.set(permisos)
        log_event(
            domain=AuditEvent.Domain.PERMISSION_MANAGEMENT, action='USER_PERMISSIONS_ASSIGNED', actor=actor,
            entity_type='user', entity_id=usuario.id, entity_name=usuario.username,
            new_values={'permissions': codenames},
            request=request,
        )
        return usuario
