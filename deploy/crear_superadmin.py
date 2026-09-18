"""Crea (o repara) la cuenta de superadministrador en una base ya migrada.

No recibe la contraseña por línea de comandos —quedaría en el historial del shell
y en la línea de comandos visible del proceso— sino por variable de entorno.
`02_crear_esquema_y_superadmin.ps1` la pide y la pasa por ahí; no hace falta
invocar este script a mano.

Variables que lee:
    SUPERADMIN_USERNAME   usuario con el que inicia sesión (también sirve el email)
    SUPERADMIN_EMAIL      correo, único en la tabla
    SUPERADMIN_PASSWORD   contraseña en claro; se hashea con Argon2 y no se imprime
    SUPERADMIN_FORZAR     '1' para reescribir la contraseña de una cuenta existente

Salida: 0 si la cuenta quedó lista, 1 si algo falló (contraseña rechazada por los
validadores, cuenta ya existente sin SUPERADMIN_FORZAR, base sin migrar).
"""

import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent / 'backend'
sys.path.insert(0, str(BASE_DIR))

import django  # noqa: E402  (después de tocar sys.path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth.password_validation import validate_password  # noqa: E402
from django.core.exceptions import ValidationError  # noqa: E402
from django.contrib.auth.models import Group  # noqa: E402
from django.db import transaction  # noqa: E402

from apps.users.models import User  # noqa: E402

ROL_ADMINISTRADOR = 'ADMINISTRADOR_GENERAL'


def fallar(mensaje):
    print(f'ERROR: {mensaje}', file=sys.stderr)
    sys.exit(1)


username = (os.getenv('SUPERADMIN_USERNAME') or '').strip()
email = (os.getenv('SUPERADMIN_EMAIL') or '').strip()
password = os.getenv('SUPERADMIN_PASSWORD') or ''
forzar = os.getenv('SUPERADMIN_FORZAR') == '1'

if not username or not email or not password:
    fallar('faltan SUPERADMIN_USERNAME, SUPERADMIN_EMAIL o SUPERADMIN_PASSWORD.')

# Que la base esté migrada se comprueba acá y no más adelante: sin esto, el error
# sería un "Invalid object name 'users_user'" de ODBC, que no dice qué hacer.
try:
    User.objects.exists()
except Exception as exc:  # noqa: BLE001 — cualquier fallo acá significa lo mismo
    fallar(f'la base no responde o no está migrada todavía ({type(exc).__name__}). '
           f'Corré `manage.py migrate` antes que este script.\n  {exc}')

existente = User.objects.filter(username__iexact=username).first() or \
    User.objects.filter(email__iexact=email).first()

if existente and not forzar:
    fallar(f'ya existe la cuenta "{existente.username}" ({existente.email}). '
           'Volvé a ejecutar con -ForzarClave si querés reescribir su contraseña.')

# Los mismos validadores que aplica la pantalla de cambio de contraseña. Se corren
# ANTES de tocar la base para no dejar una cuenta a medio crear.
try:
    validate_password(password, user=existente or User(username=username, email=email))
except ValidationError as exc:
    fallar('la contraseña no pasa los validadores de Django:\n  - ' + '\n  - '.join(exc.messages))

with transaction.atomic():
    usuario = existente or User(username=username, email=email)
    usuario.username = username
    usuario.email = email
    usuario.is_superuser = True
    usuario.is_staff = True
    usuario.status = User.Status.ACTIVE
    # `must_change_password` queda en False a propósito: el campo existe y se edita
    # desde la administración de usuarios, pero el login no implementa todavía un
    # flujo que obligue a cambiarla al entrar, así que activarlo acá no forzaría
    # nada y solo confundiría al leer la ficha del usuario.
    usuario.must_change_password = False
    usuario.set_password(password)  # Argon2, nunca asignación directa a .password
    usuario.save()

    rol = Group.objects.filter(name=ROL_ADMINISTRADOR).first()
    if rol:
        usuario.groups.add(rol)

# Se verifica contra el hash guardado, no contra la variable: si `set_password` o el
# hasher fallaran en silencio, el script tiene que decirlo acá y no el día que
# alguien no pueda entrar.
usuario.refresh_from_db()
if not usuario.check_password(password):
    fallar('la contraseña no se guardó correctamente (check_password falló tras el alta).')

accion = 'actualizada' if existente else 'creada'
roles = ', '.join(g.name for g in usuario.groups.all()) or '(ninguno)'
print(f'Cuenta {accion}: {usuario.username} <{usuario.email}>')
print(f'  superusuario : {usuario.is_superuser}   activa: {usuario.is_active}')
print(f'  roles        : {roles}')
if not Group.objects.filter(name=ROL_ADMINISTRADOR).exists():
    print(f'  AVISO: no existe el rol {ROL_ADMINISTRADOR}. Como superusuario tiene todos los '
          'permisos igual, pero revisá que las migraciones de `apps.roles` hayan corrido.')
