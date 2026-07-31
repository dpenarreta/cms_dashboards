from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import User


@receiver(post_save, sender=User)
def revoke_sessions_when_user_disabled(sender, instance, **kwargs):
    """Invariante: usuario sin `is_active` ⇒ sin sesiones activas, sea cual sea la vía por la que
    cambió (endpoint admin, `manage.py shell`, etc.)."""
    if instance.is_active:
        return
    from apps.authentication.models import Session
    Session.objects.filter(user=instance, revoked_at__isnull=True).update(revoked_at=timezone.now())
