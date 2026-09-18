"""Genera el hash Argon2 de una contraseña, para pasárselo a `02_crear_esquema.sql`.

SQL Server no puede calcular un hash de Django, así que la cuenta de administrador se
crea con el hash ya resuelto. Este script lo produce usando exactamente el mismo
hasher que la aplicación (Argon2, primero en PASSWORD_HASHERS), de modo que el
resultado es indistinguible de una contraseña establecida desde la pantalla.

La contraseña se pide de forma interactiva: no se pasa por argumento para que no quede
en el historial del shell ni en la línea de comandos del proceso.

    python deploy/generar_hash.py

Imprime una sola línea: el hash. Se lo pasa a sqlcmd con
`-v SuperadminHash="<lo que imprime>"`.
"""

import getpass
import os
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / 'backend'))

import django  # noqa: E402

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
# El hash no depende de la base, pero settings exige claves reales con DEBUG=False.
os.environ.setdefault('DEBUG', 'True')
django.setup()

from django.contrib.auth.hashers import make_password  # noqa: E402
from django.contrib.auth.password_validation import validate_password  # noqa: E402
from django.core.exceptions import ValidationError  # noqa: E402

clave = os.environ.get('SUPERADMIN_PASSWORD') or getpass.getpass('Contraseña del administrador: ')
if not clave:
    sys.exit('No se ingresó ninguna contraseña.')

try:
    validate_password(clave)
except ValidationError as exc:
    print('AVISO: la contraseña no pasaría los validadores de la aplicación:', file=sys.stderr)
    for mensaje in exc.messages:
        print(f'  - {mensaje}', file=sys.stderr)
    print('  (el hash se genera igual; la pantalla de cambio de contraseña sí la rechazaría)',
          file=sys.stderr)

hash_generado = make_password(clave)
# Se verifica antes de entregarlo: un hash mal formado solo se descubriría el día que
# alguien no pueda entrar.
from django.contrib.auth.hashers import check_password  # noqa: E402

if not check_password(clave, hash_generado):
    sys.exit('El hash generado no valida contra la contraseña. No lo uses.')

print(hash_generado)
