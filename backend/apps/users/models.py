from django.contrib.auth.models import AbstractUser
from django.db import models

from apps.core.models import BaseModel


class User(AbstractUser, BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Activo'
        DISABLED = 'disabled', 'Deshabilitado'
        BLOCKED = 'blocked', 'Bloqueado'

    email = models.EmailField(unique=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)
    must_change_password = models.BooleanField(default=False)
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
