import uuid

from django.conf import settings
from django.db import models


class Dashboard(models.Model):
    """Un dashboard por área, creado dinámicamente por un administrador. Cada uno aloja el mismo
    pipeline de carga y cálculo de KPIs de cartera (ver `cartera/services/dashboard_layout.py` y
    `cartera/views.py`) — no existe ya un único dashboard especial con lógica propia."""

    dashboard_id = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    area = models.CharField(max_length=100, blank=True, default='')
    description = models.CharField(max_length=300, blank=True, default='')
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.dashboard_id})'


class CargaArchivo(models.Model):
    class Estado(models.TextChoices):
        SUBIDO = 'SUBIDO', 'Subido'
        VALIDADO = 'VALIDADO', 'Validado'
        PROCESADO = 'PROCESADO', 'Procesado'
        ERROR = 'ERROR', 'Error'

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # `default='cartera'`: valor histórico (preserva compatibilidad con cargas anteriores a la
    # existencia de este campo) — cada carga nueva manda su `dashboard_id` real explícitamente.
    dashboard_id = models.SlugField(max_length=100, default='cartera', db_index=True)
    nombre_original = models.CharField(max_length=255)
    nombre_hoja = models.CharField(max_length=255, blank=True)
    tamano_bytes = models.BigIntegerField(default=0)
    fecha_carga = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.SUBIDO)
    fecha_corte = models.DateField(null=True, blank=True)

    total_filas_excel = models.IntegerField(default=0)
    filas_validas = models.IntegerField(default=0)
    filas_advertencia = models.IntegerField(default=0)
    filas_descartadas = models.IntegerField(default=0)

    mapeo_columnas = models.JSONField(default=dict, blank=True)
    resumen_validacion = models.JSONField(default=dict, blank=True)

    archivo_temp_nombre = models.CharField(max_length=255, blank=True, default='')

    class Meta:
        ordering = ['-fecha_carga']

    def __str__(self):
        return f'{self.nombre_original} ({self.id})'


class RegistroCartera(models.Model):
    carga = models.ForeignKey(CargaArchivo, related_name='registros', on_delete=models.CASCADE)

    cliente = models.CharField(max_length=255, blank=True, default='')
    ruc_cliente = models.CharField(max_length=50, blank=True, default='')
    codigo_cliente = models.CharField(max_length=100, blank=True, default='')
    identificador_cliente = models.CharField(max_length=255, db_index=True)

    sucursal = models.CharField(max_length=255, blank=True, default='')
    ciudad = models.CharField(max_length=255, db_index=True, default='SIN CIUDAD')
    zona = models.CharField(max_length=255, blank=True, default='')
    vendedor_ejecutivo = models.CharField(max_length=255, blank=True, default='')
    estado_cliente = models.CharField(max_length=100, blank=True, default='')
    telefono = models.CharField(max_length=50, blank=True, default='')
    direccion = models.TextField(blank=True, default='')

    numero_documento = models.CharField(max_length=100, db_index=True, default='')
    fecha_emision = models.DateField(null=True, blank=True)
    fecha_vencimiento = models.DateField(null=True, blank=True, db_index=True)
    saldo = models.DecimalField(max_digits=18, decimal_places=2, db_index=True)

    articulo = models.CharField(max_length=255, blank=True, default='')
    vence_original = models.CharField(max_length=100, blank=True, default='')
    observacion = models.TextField(blank=True, default='')
    mes = models.CharField(max_length=50, blank=True, default='')
    tipo_venta = models.CharField(max_length=100, blank=True, default='')
    causal = models.CharField(max_length=100, db_index=True, default='SIN GESTIÓN')
    producto = models.CharField(max_length=255, blank=True, default='')
    fecha_compromiso_pago = models.DateField(null=True, blank=True)
    observaciones = models.TextField(blank=True, default='')
    tipo_cartera = models.CharField(max_length=100, blank=True, default='')
    recuperador = models.CharField(max_length=255, db_index=True, default='SIN RECUPERADOR ASIGNADO')
    dias_credito = models.IntegerField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['carga', 'fecha_vencimiento']),
            models.Index(fields=['carga', 'recuperador']),
            models.Index(fields=['carga', 'causal']),
            models.Index(fields=['carga', 'ciudad']),
        ]

    def __str__(self):
        return f'{self.cliente} - {self.numero_documento}'


class DashboardLayout(models.Model):
    """Configuración de layout de un dashboard (sección 17). Una fila por `dashboard_id` con
    alcance GENERAL; `POR_ROL`/`POR_USUARIO` quedan modelados para una fase futura (sección 18),
    no implementados todavía."""

    class Alcance(models.TextChoices):
        GENERAL = 'GENERAL', 'General'
        POR_ROL = 'POR_ROL', 'Por rol'
        POR_USUARIO = 'POR_USUARIO', 'Por usuario'

    dashboard_id = models.SlugField(max_length=100, unique=True)
    version = models.PositiveIntegerField(default=1)
    scope = models.CharField(max_length=20, choices=Alcance.choices, default=Alcance.GENERAL)
    theme = models.JSONField(default=dict, blank=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.dashboard_id} (v{self.version})'


class DashboardComponent(models.Model):
    """Un componente posicionable del grid (KPI, gráfico, filtro, mensaje, tabla, título...).
    Sección 8: el drag and drop no se limita a gráficos, por eso el modelo es genérico."""

    class Tipo(models.TextChoices):
        KPI = 'kpi', 'Tarjeta KPI'
        CHART = 'chart', 'Gráfico'
        FILTER = 'filter', 'Filtro'
        FILTERS_PANEL = 'filters_panel', 'Panel de filtros'
        MESSAGE = 'message', 'Mensaje'
        ALERT = 'alert', 'Alerta'
        TABLE = 'table', 'Tabla'
        TITLE = 'title', 'Título'
        TEXT = 'text', 'Texto'

    layout = models.ForeignKey(DashboardLayout, related_name='components', on_delete=models.CASCADE)
    component_id = models.SlugField(max_length=100)
    type = models.CharField(max_length=20, choices=Tipo.choices)
    chart_type = models.CharField(max_length=30, blank=True, default='')  # modelado, no editable aún

    row = models.PositiveIntegerField(default=1)
    order = models.PositiveIntegerField(default=1)
    width = models.PositiveSmallIntegerField(default=12)
    height = models.PositiveIntegerField(default=400)
    is_visible = models.BooleanField(default=True)

    content = models.JSONField(default=dict, blank=True)
    styles = models.JSONField(default=dict, blank=True)
    config = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = [('layout', 'component_id')]
        ordering = ['row', 'order']

    def __str__(self):
        return f'{self.component_id} ({self.type})'


class DashboardAuditLog(models.Model):
    """Historial de cambios de layout (sección 19). No se borra al restablecer el diseño."""

    class TipoCambio(models.TextChoices):
        ORDEN = 'CAMBIO_DE_ORDEN', 'Cambio de orden'
        TAMANO = 'CAMBIO_DE_TAMANO', 'Cambio de tamaño'
        COLOR = 'CAMBIO_DE_COLOR', 'Cambio de color'
        TEXTO = 'CAMBIO_DE_TEXTO', 'Cambio de texto'
        CONFIG = 'CAMBIO_DE_CONFIGURACION', 'Cambio de configuración'
        OCULTADO = 'COMPONENTE_OCULTADO', 'Componente ocultado'
        ELIMINADO = 'COMPONENTE_ELIMINADO', 'Componente eliminado'
        RESTABLECIDO = 'DISENO_RESTABLECIDO', 'Diseño restablecido'

    dashboard_id = models.SlugField(max_length=100)
    component_id = models.SlugField(max_length=100, blank=True, default='')
    change_type = models.CharField(max_length=30, choices=TipoCambio.choices)
    changed_by = models.CharField(max_length=150, blank=True, default='Anónimo')
    changed_at = models.DateTimeField(auto_now_add=True)
    version = models.PositiveIntegerField(default=1)
    previous_config = models.JSONField(default=dict, blank=True)
    new_config = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['-changed_at']

    def __str__(self):
        return f'{self.dashboard_id}/{self.component_id or "-"}: {self.change_type}'
