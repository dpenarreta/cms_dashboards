"""Saneo del HTML de las plantillas de correo.

`EmailTemplate.html_body` lo escribe un usuario con `configuracion.editar` desde un editor de texto
enriquecido, y el HTML guardado se vuelve a cargar en ese editor cada vez que alguien abre la
pantalla. El modelo documenta que ese HTML se trata como confiado, y a ese nivel de permiso es una
decisión razonable — pero deja dos huecos que este módulo cierra:

- `quill` 2.0.3 (vía `react-quill-new`) tiene un XSS reportado sin corrección upstream: 2.0.3 es la
  última versión que existe. Lo que se guarda hoy es lo que el editor de mañana va a parsear, así
  que el HTML almacenado es la superficie de ataque, no la sesión que lo escribió.
- Una sesión de administrador comprometida podría dejar HTML ejecutable persistido para el próximo
  administrador que abra la pantalla.

## Por qué no basta con sanear y listo

El cuerpo de un correo es un DOCUMENTO HTML completo, no un fragmento: el valor por defecto trae
`<!DOCTYPE>`, `<html>`, `<head><meta charset>` y un `<body style="background: #eeeeee; padding:
24px">` del que depende el aspecto del correo. Los saneadores trabajan sobre fragmentos y descartan
esa estructura — se comprobó con la plantilla real: tanto `nh3` como `bleach` se comen el `<body>`
entero y con él su fondo y su padding. `bleach`, además, borra TODOS los `style` en línea salvo que
se le configure un saneador de CSS aparte, y un correo sin estilos en línea no tiene diseño: el
resultado era irreconocible.

De ahí el planteo de acá: el CONTENIDO lo sanea `nh3` (que sí conserva los `style` en línea), y el
esqueleto del documento lo reconstruimos nosotros a partir de una plantilla fija. Como efecto
secundario, el esqueleto deja de ser controlable por el usuario, lo que elimina de raíz
`<meta http-equiv="refresh">`, `<base href>` y `<style>` en el `<head>`.

La extracción del `<body>` usa `html.parser` de la biblioteca estándar y NO es la parte que da la
seguridad: todo lo que sale de ahí pasa igual por `nh3`. Si la extracción fallara, el peor caso es
que se sanee el documento entero como fragmento — se pierde fidelidad, nunca seguridad.
"""

from html.parser import HTMLParser

import nh3

# Etiquetas que tienen sentido en un correo. Es más ancha que lo que produce el editor (que solo
# genera encabezados, negrita/cursiva/subrayado, color, alineación, listas y enlaces) porque el
# valor por defecto y cualquier plantilla pegada desde una herramienta de correo usan tablas y
# `div`s para maquetar: recortarlo al editor rompería plantillas legítimas.
ETIQUETAS_PERMITIDAS = {
    'a', 'b', 'blockquote', 'br', 'center', 'div', 'em', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'hr', 'i', 'img', 'li', 'ol', 'p', 'pre', 'small', 'span', 'strong', 's', 'sub', 'sup',
    'table', 'tbody', 'td', 'tfoot', 'th', 'thead', 'tr', 'u', 'ul',
}

# `style` en casi todo, a propósito: un correo se maqueta con estilos en línea porque los clientes
# de correo ignoran las hojas de estilo. Quitarlo sería "sanear" el diseño, no el riesgo.
_COMUNES = {'style', 'class', 'align', 'title', 'dir'}
ATRIBUTOS_PERMITIDOS = {
    '*': _COMUNES,
    'a': _COMUNES | {'href', 'target', 'name'},
    'img': _COMUNES | {'src', 'alt', 'width', 'height'},
    'td': _COMUNES | {'colspan', 'rowspan', 'valign', 'width', 'height', 'bgcolor'},
    'th': _COMUNES | {'colspan', 'rowspan', 'valign', 'width', 'height', 'bgcolor'},
    'table': _COMUNES | {'border', 'cellpadding', 'cellspacing', 'width', 'bgcolor', 'role'},
    'tr': _COMUNES | {'valign', 'bgcolor'},
    'ol': _COMUNES | {'type', 'start'},
    'li': _COMUNES | {'value', 'data-list'},  # `data-list` es cómo quill 2 marca viñeta vs. número
}

# Sin `data:` ni `javascript:`. `cid:` queda fuera porque este proyecto no adjunta imágenes en el
# correo; si algún día lo hiciera, agregarlo acá es el único cambio necesario.
ESQUEMAS_PERMITIDOS = {'http', 'https', 'mailto', 'tel'}

_ESQUELETO = (
    '<!DOCTYPE html>\n<html lang="es">\n<head><meta charset="utf-8"></head>\n'
    '<body{estilo}>\n{contenido}\n</body>\n</html>\n'
)


class _ExtractorDeCuerpo(HTMLParser):
    """Ubica el `<body>` para conservar su `style` y quedarse con su contenido.

    Reconstruye el contenido a partir de los eventos del parser en vez de calcular offsets sobre el
    texto original: `getpos()` da (línea, columna) y convertirlo a un índice absoluto a mano es
    justo el tipo de cuenta que se rompe con un salto de línea dentro de una etiqueta.
    `convert_charrefs=False` evita decodificar entidades acá para volver a codificarlas después.

    No decide nada de seguridad — solo recorta; lo que sale de acá pasa igual por `nh3`.
    """

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.estilo_cuerpo = None
        self._dentro = False
        self._termino = False
        self._piezas = []

    def handle_starttag(self, tag, attrs):
        if tag == 'body' and not self._dentro and not self._termino:
            self.estilo_cuerpo = dict(attrs).get('style')
            self._dentro = True
            return
        self._agregar(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self._agregar(self.get_starttag_text())

    def handle_endtag(self, tag):
        if tag == 'body' and self._dentro:
            self._dentro = False
            self._termino = True
            return
        self._agregar(f'</{tag}>')

    def handle_data(self, data):
        self._agregar(data)

    def handle_entityref(self, name):
        self._agregar(f'&{name};')

    def handle_charref(self, name):
        self._agregar(f'&#{name};')

    def handle_comment(self, data):
        self._agregar(f'<!--{data}-->')

    def _agregar(self, texto):
        if self._dentro and texto:
            self._piezas.append(texto)

    @property
    def contenido(self):
        return ''.join(self._piezas) if self._termino else None


def _separar_documento(html):
    """Devuelve `(estilo_del_body, contenido)`.

    Si el HTML no es un documento completo (no hay un `<body>` cerrado), se lo trata entero como
    fragmento y el estilo queda en `None`.
    """
    extractor = _ExtractorDeCuerpo()
    try:
        extractor.feed(html)
        extractor.close()
    except Exception:  # noqa: BLE001 - un HTML que ni se puede recorrer se sanea completo
        return None, html

    contenido = extractor.contenido
    if contenido is None:
        return None, html
    return extractor.estilo_cuerpo, contenido


def _sanear_fragmento(fragmento):
    return nh3.clean(
        fragmento,
        tags=ETIQUETAS_PERMITIDAS,
        attributes=ATRIBUTOS_PERMITIDOS,
        url_schemes=ESQUEMAS_PERMITIDOS,
        # `link_rel=None` para no inyectar `rel="noopener noreferrer"` en cada enlace: en un correo
        # no aporta nada (no hay `window.opener`) y ensucia el HTML que el usuario vuelve a ver.
        link_rel=None,
        strip_comments=True,
    )


def _sanear_estilo(estilo):
    """Pasa el `style` del `<body>` por el mismo saneador, dentro de un `<div>` desechable.

    Reutilizar `nh3` en vez de escribir una validación de CSS propia: si alguna vez el saneador
    aprende a filtrar CSS, este atributo se beneficia solo.
    """
    if not estilo:
        return ''
    limpio = _sanear_fragmento(f'<div style="{estilo}"></div>')
    inicio = limpio.find('style="')
    if inicio == -1:
        return ''
    fin = limpio.find('"', inicio + len('style="'))
    return limpio[inicio + len('style="'):fin] if fin != -1 else ''


def sanear_html_de_correo(html):
    """Sanea el cuerpo de una plantilla de correo conservando su estructura de documento.

    Un documento completo vuelve como documento completo (con el esqueleto reconstruido y el
    `style` del `<body>` conservado); un fragmento vuelve como fragmento.
    """
    if not html or not html.strip():
        return html

    estilo, contenido = _separar_documento(html)
    contenido_limpio = _sanear_fragmento(contenido)
    if estilo is None:
        return contenido_limpio

    estilo_limpio = _sanear_estilo(estilo)
    atributo = f' style="{estilo_limpio}"' if estilo_limpio else ''
    return _ESQUELETO.format(estilo=atributo, contenido=contenido_limpio.strip())
