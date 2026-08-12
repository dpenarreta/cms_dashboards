"""Interpretación del dashboard generada por IA — dos variantes que comparten la misma
descripción por componente (`_describir_componente`) y la misma llamada a Gemini:

- `generar_interpretacion`: un único párrafo narrativo de TODO el dashboard a la vez (botón
  "Interpretación completa" en `DashboardAreaPage.jsx`, antes de "Conectar vista de base de
  datos").
- `generar_hallazgos_ia`: un párrafo corto POR componente (`{component_id: texto}`), en un único
  llamado batch a Gemini (no uno por componente — evitaría N llamadas externas por cada carga de
  página). Reemplaza progresivamente, componente por componente, los "Hallazgos clave" generados
  con reglas fijas en el frontend (`frontend/src/utils/hallazgosClave.js`,
  `HallazgosClaveCard.jsx`), que siguen siendo el fallback instantáneo mientras este endpoint
  resuelve o si falla.

Ambas parten de los mismos datos ya calculados que sirve `serializar_layout` (`content` de cada
componente visible) — no reprocesan ningún archivo ni vuelven a consultar `RegistroCartera`.
"""

import json

import requests
from django.conf import settings

from ..exceptions import CarteraError
from ..models import Dashboard
from . import dashboard_layout as dl

_GEMINI_URL = 'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent'
_TIMEOUT_SEGUNDOS = 45
_MAXIMO_ITEMS_POR_COMPONENTE = 20


def _formatear_numero(valor):
    if isinstance(valor, float):
        return f'{valor:,.2f}'
    if isinstance(valor, int):
        return f'{valor:,}'
    return str(valor)


def _describir_kpi(content):
    texto = f'KPI "{content.get("titulo") or "(sin título)"}": valor = {_formatear_numero(content.get("valor"))}.'
    if content.get('descripcion'):
        texto += f' {content["descripcion"]}'
    return texto


def _describir_categorico(content):
    categorias = content.get('categorias') or []
    valores = content.get('valores') or []
    pares = list(zip(categorias, valores))[:_MAXIMO_ITEMS_POR_COMPONENTE]
    detalle = ', '.join(f'{c}: {_formatear_numero(v)}' for c, v in pares)
    truncado = ' (truncado a los primeros items)' if len(categorias) > _MAXIMO_ITEMS_POR_COMPONENTE else ''
    return f'Gráfico "{content.get("titulo") or "(sin título)"}" — {detalle}{truncado}.'


def _describir_multiserie(content):
    categorias = content.get('categorias') or []
    series = content.get('series') or []
    partes = []
    for serie in series:
        pares = list(zip(categorias, serie.get('valores') or []))[:_MAXIMO_ITEMS_POR_COMPONENTE]
        detalle = ', '.join(f'{c}: {_formatear_numero(v)}' for c, v in pares)
        partes.append(f'serie "{serie.get("nombre")}" ({detalle})')
    truncado = ' (truncado a los primeros items)' if len(categorias) > _MAXIMO_ITEMS_POR_COMPONENTE else ''
    return f'Gráfico multiserie "{content.get("titulo") or "(sin título)"}" — ' + '; '.join(partes) + f'{truncado}.'


def _describir_dispersion(content):
    puntos = (content.get('puntos') or [])[:_MAXIMO_ITEMS_POR_COMPONENTE]
    detalle = ', '.join(f'({p.get("x")}, {p.get("y")})' for p in puntos)
    truncado = ' (truncado a los primeros puntos)' if len(content.get('puntos') or []) > _MAXIMO_ITEMS_POR_COMPONENTE else ''
    return f'Gráfico de dispersión "{content.get("titulo") or "(sin título)"}" — puntos (x, y): {detalle}{truncado}.'


def _describir_tabla(content):
    columnas = content.get('columnas') or []
    filas = (content.get('filas') or [])[:_MAXIMO_ITEMS_POR_COMPONENTE]
    encabezado = ' | '.join(str(c) for c in columnas)
    filas_texto = ' / '.join(' | '.join(_formatear_numero(v) for v in fila) for fila in filas)
    truncado = ' (truncado a las primeras filas)' if len(content.get('filas') or []) > _MAXIMO_ITEMS_POR_COMPONENTE else ''
    total = content.get('total')
    texto = f'Tabla "{content.get("titulo") or "(sin título)"}" — columnas: {encabezado}. Filas: {filas_texto}{truncado}.'
    if total:
        texto += f' Total: {" | ".join(_formatear_numero(v) for v in total)}.'
    return texto


def _describir_componente(componente):
    content = componente.get('content') or {}
    if componente['type'] == 'kpi':
        return _describir_kpi(content)
    if componente['type'] != 'chart':
        return None
    if 'puntos' in content:
        return _describir_dispersion(content)
    if 'columnas' in content and 'filas' in content:
        return _describir_tabla(content)
    if 'series' in content:
        return _describir_multiserie(content)
    if 'categorias' in content:
        return _describir_categorico(content)
    return None


def _construir_prompt(dashboard, componentes_descritos):
    cuerpo = '\n'.join(f'- {texto}' for texto in componentes_descritos)
    return (
        'Sos un analista de datos redactando para un directivo que no vio el dashboard. '
        f'A continuación tenés los componentes (KPIs, gráficos y tablas) del dashboard '
        f'"{dashboard.name}" (área: {dashboard.area or "sin área"}), con sus datos ya calculados:\n\n'
        f'{cuerpo}\n\n'
        'Redactá una interpretación completa y ejecutiva en español, en prosa clara (párrafos, no '
        'una lista mecánica de cada número), que resuma la situación general, destaque los '
        'hallazgos más relevantes (valores más altos/bajos, concentraciones, proporciones) y '
        'señale relaciones entre componentes si son evidentes a partir de los datos provistos. '
        'No inventes datos que no estén en la información de arriba.'
    )


def _construir_prompt_hallazgos(dashboard, items):
    cuerpo = '\n'.join(f'- ID "{component_id}": {texto}' for component_id, texto in items)
    return (
        'Sos un analista de datos. Para cada componente del dashboard '
        f'"{dashboard.name}" (área: {dashboard.area or "sin área"}) listado abajo (con su ID y sus '
        'datos ya calculados), escribí un párrafo breve (1 a 3 oraciones) de "hallazgo clave": el '
        'punto más relevante que ESE componente en particular muestra, en español, con los números '
        'y nombres importantes resaltados entre **dobles asteriscos**. Analizá cada componente de '
        'forma independiente, sin compararlo con los demás. No inventes datos que no estén en la '
        'información provista.\n\n'
        f'Componentes:\n{cuerpo}\n\n'
        'Devolvé ÚNICAMENTE un objeto JSON plano (sin texto adicional, sin bloque de código) con '
        'esta forma exacta: {"<ID>": "<párrafo>", ...}, con exactamente una entrada por cada ID '
        'listado arriba, usando el ID tal cual (sin el prefijo "ID").'
    )


def _dashboard_y_componentes_visibles(dashboard_id, mensaje_sin_datos):
    if not settings.GEMINI_API_KEY:
        raise CarteraError(
            'La interpretación con IA no está configurada en este entorno.', codigo='IA_NO_CONFIGURADA',
        )

    try:
        dashboard = Dashboard.objects.get(dashboard_id=dashboard_id)
    except Dashboard.DoesNotExist:
        raise CarteraError('El dashboard indicado no existe.', codigo='DASHBOARD_NO_ENCONTRADO')

    layout = dl.obtener_o_crear_layout(dashboard_id)
    visibles = [c for c in dl.serializar_layout(layout)['components'] if c['is_visible']]
    items = [(c['component_id'], _describir_componente(c)) for c in visibles]
    items = [(component_id, texto) for component_id, texto in items if texto]

    if not items:
        raise CarteraError(mensaje_sin_datos, codigo='SIN_DATOS')

    return dashboard, items


def _llamar_gemini(payload):
    url = _GEMINI_URL.format(model=settings.GEMINI_MODEL)
    try:
        respuesta = requests.post(url, params={'key': settings.GEMINI_API_KEY}, json=payload, timeout=_TIMEOUT_SEGUNDOS)
    except requests.RequestException:
        raise CarteraError(
            'No se pudo contactar al servicio de interpretación con IA. Intente nuevamente.', codigo='IA_ERROR',
        )

    if respuesta.status_code != 200:
        raise CarteraError(
            'El servicio de interpretación con IA respondió con un error. Intente nuevamente.',
            codigo='IA_ERROR',
            detalles={'status_code': respuesta.status_code},
        )

    cuerpo = respuesta.json()
    try:
        return cuerpo['candidates'][0]['content']['parts'][0]['text']
    except (KeyError, IndexError):
        raise CarteraError(
            'El servicio de interpretación con IA no devolvió una respuesta utilizable.', codigo='IA_ERROR',
        )


def generar_interpretacion(dashboard_id):
    dashboard, items = _dashboard_y_componentes_visibles(
        dashboard_id, 'Este dashboard no tiene componentes con datos para interpretar.',
    )
    prompt = _construir_prompt(dashboard, [texto for _, texto in items])
    texto = _llamar_gemini({'contents': [{'parts': [{'text': prompt}]}]})
    return texto.strip()


def generar_hallazgos_ia(dashboard_id):
    dashboard, items = _dashboard_y_componentes_visibles(
        dashboard_id, 'Este dashboard no tiene componentes con datos para generar hallazgos.',
    )
    prompt = _construir_prompt_hallazgos(dashboard, items)
    texto_json = _llamar_gemini({
        'contents': [{'parts': [{'text': prompt}]}],
        'generationConfig': {'responseMimeType': 'application/json'},
    })

    try:
        hallazgos = json.loads(texto_json)
    except json.JSONDecodeError:
        raise CarteraError(
            'El servicio de interpretación con IA no devolvió una respuesta utilizable.', codigo='IA_ERROR',
        )
    if not isinstance(hallazgos, dict):
        raise CarteraError(
            'El servicio de interpretación con IA no devolvió una respuesta utilizable.', codigo='IA_ERROR',
        )

    ids_validos = {component_id for component_id, _ in items}
    return {
        component_id: texto for component_id, texto in hallazgos.items()
        if component_id in ids_validos and isinstance(texto, str) and texto.strip()
    }
