"""Validación por firma binaria de las imágenes que suben los usuarios.

`.claude/rules/security.md` exige que todo archivo subido se valide por extensión **y** por firma
binaria. La carga de Excel ya lo cumplía (`cartera.services.excel_reader.validar_extension_y_firma`);
la subida de avatar no, y ahí el hueco era peor de lo que aparenta.

`serializers.ImageField` de DRF delega en el `ImageField` de formularios de Django, que llama a
`Image.open()` y **recién después** corre `validate_image_file_extension`. O sea que la extensión no
filtra nada: cuando el validador de extensión opina, Pillow ya parseó el archivo. Y Pillow despacha
por la firma binaria del contenido, no por el nombre — se comprobó que un GIF renombrado a
`avatar.png` se aceptaba y lo procesaba `GifImagePlugin`.

Consecuencia: cualquier usuario autenticado alcanzaba los ~40 plugins de formato que Pillow registra
(PSD, FITS, GD, JPEG2000, McIdas...), que es justamente donde estaban los 12 avisos de seguridad que
motivaron la actualización a Pillow 12.3. Actualizar cerró los fallos conocidos; esto reduce la
superficie para los que todavía no se conocen: con la firma verificada antes de abrir el archivo,
solo tres plugins llegan a tocar los bytes.

No usa `CarteraError` sino el `ValidationError` de DRF, por el mismo motivo que
`apps.core.password`: es un error de validación de un campo concreto y el contrato de error global
ya lo traduce a 400 con el detalle por campo.
"""

import os

from rest_framework import serializers

# Suficiente para la firma más larga de las tres: WebP necesita los bytes 0-3 ('RIFF') y 8-11
# ('WEBP'), con el tamaño del archivo en medio.
BYTES_DE_CABECERA = 12


def _es_webp(cabecera):
    return cabecera[:4] == b'RIFF' and cabecera[8:12] == b'WEBP'


# PNG, JPEG y WebP cubren lo que produce cualquier teléfono o escritorio. GIF queda fuera a
# propósito: un avatar animado es un caso raro y admitirlo reagrega un plugin entero de superficie.
# Si alguna vez hace falta, es una línea más acá — pero que sea una decisión, no un descuido.
FORMATOS_PERMITIDOS = (
    ('PNG', {'.png'}, lambda cabecera: cabecera.startswith(b'\x89PNG\r\n\x1a\n')),
    ('JPEG', {'.jpg', '.jpeg'}, lambda cabecera: cabecera.startswith(b'\xff\xd8\xff')),
    ('WEBP', {'.webp'}, _es_webp),
)

FORMATOS_LEGIBLES = 'PNG, JPEG y WebP'


def detectar_formato(cabecera):
    """Nombre del formato cuya firma coincide con `cabecera`, o `None` si no es ninguno permitido."""
    for nombre, _extensiones, coincide in FORMATOS_PERMITIDOS:
        if coincide(cabecera):
            return nombre
    return None


def validar_extension_y_firma(nombre_archivo, cabecera):
    """Comprueba que el contenido sea un formato permitido y que la extensión se corresponda.

    Devuelve el nombre del formato detectado (`'PNG'`, `'JPEG'` o `'WEBP'`), que el llamador puede
    contrastar después contra el formato con el que Pillow terminó abriendo el archivo.

    Las dos comprobaciones son necesarias y ninguna sustituye a la otra: la firma es lo que decide
    qué parser de Pillow corre, y la extensión es lo que decide con qué `Content-Type` se sirve
    después el archivo desde `MEDIA_ROOT`.
    """
    formato = detectar_formato(cabecera)
    if formato is None:
        raise serializers.ValidationError(
            f'El contenido del archivo no es una imagen {FORMATOS_LEGIBLES}.'
        )

    extensiones = next(e for nombre, e, _ in FORMATOS_PERMITIDOS if nombre == formato)
    _, extension = os.path.splitext((nombre_archivo or '').lower())
    if extension not in extensiones:
        esperadas = ' o '.join(sorted(extensiones))
        raise serializers.ValidationError(
            f'La extensión "{extension}" no corresponde al contenido del archivo, que es {formato} '
            f'(se esperaba {esperadas}).'
        )
    return formato


def _leer_cabecera(archivo):
    posicion = archivo.tell()
    archivo.seek(0)
    cabecera = archivo.read(BYTES_DE_CABECERA)
    archivo.seek(posicion)
    return cabecera


class CampoImagenSegura(serializers.ImageField):
    """`ImageField` que valida la firma binaria ANTES de dejar que Pillow abra el archivo.

    El orden es todo el punto de esta clase: `super().to_internal_value(data)` es lo que termina
    llamando a `Image.open()`, así que la comprobación de firma tiene que ir antes de esa línea. Si
    se moviera después (por ejemplo, a un `validate_<campo>` del serializer) seguiría rechazando los
    mismos archivos, pero ya no protegería de nada — Pillow habría parseado igual.
    """

    def to_internal_value(self, data):
        if not hasattr(data, 'read'):
            # No es un archivo subido; que DRF produzca su error habitual de "no se envió archivo".
            return super().to_internal_value(data)

        formato = validar_extension_y_firma(getattr(data, 'name', ''), _leer_cabecera(data))
        archivo = super().to_internal_value(data)

        # Segunda barrera: el formato con el que Pillow abrió el archivo debe ser el que anunciaba
        # la firma. Cubre el caso de un contenido ambiguo que dos plugins acepten.
        formato_abierto = getattr(getattr(archivo, 'image', None), 'format', None)
        if formato_abierto is not None and formato_abierto != formato:
            raise serializers.ValidationError(
                f'El contenido del archivo se abrió como {formato_abierto} pero su firma decía '
                f'{formato}.'
            )
        return archivo
