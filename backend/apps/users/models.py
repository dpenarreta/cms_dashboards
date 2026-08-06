import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseModel


def avatar_upload_to(instance, filename):
    # Nombre aleatorio (nunca el original) — mismo criterio de seguridad que los archivos
    # temporales de `cartera` (ver `@.claude/rules/security.md`).
    extension = filename.rsplit('.', 1)[-1].lower() if '.' in filename else 'jpg'
    return f'avatars/{uuid.uuid4()}.{extension}'


class User(AbstractUser, BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        DISABLED = 'disabled', 'Deshabilitado'
        BLOCKED = 'blocked', 'Bloqueado'

    email = models.EmailField(unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    must_change_password = models.BooleanField(default=False)
    area = models.CharField(max_length=100, blank=True, default='')
    avatar = models.ImageField(upload_to=avatar_upload_to, blank=True, null=True)
    created_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='created_users',
    )
    updated_by = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True, related_name='updated_users',
    )

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    def save(self, *args, **kwargs):
        self.is_active = self.status == self.Status.ACTIVE
        super().save(*args, **kwargs)
