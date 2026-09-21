import uuid

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models


class Dashboard(models.Model):
    """Un dashboard por área, creado dinámicamente por un administrador. Cada uno aloja el mismo
    pipeline de carga y cálculo de KPIs de cartera (ver `cartera/services/dashboard_layout.py` y
    `cartera/views.py`) — no existe ya un único dashboard especial con lógica propia."""

    dashboard_id = models.SlugField(max_length=100, unique=True)
    name = models.CharField(max_length=150)
    area = models.CharField(max_length=100, blank=True, default='')
    description = models.CharField(max_length=300, blank=True, default='')
    # Texto libre, editable en creación y edición, pensado únicamente para orientar a la IA
    # (`services/dashboard_interpretation.py`) sobre qué es este dashboard y qué representan sus
    # datos — nunca se renderiza dentro del dashboard en sí, a diferencia de `description`.
    contexto = models.TextField(blank=True, default='')

    class FuenteBDTipo(models.TextChoices):
        VISTA = 'vista', 'Vista'
        PROCEDIMIENTO = 'procedimiento', 'Procedimiento almacenado'

    # Fuente de datos externa opcional para este dashboard/pestaña puntual ("Conectar vista de
    # base de datos" en `DashboardAreaPage.jsx`) — la conexión en sí (servidor/credenciales) es
    # una única conexión "por defecto" a nivel de app (`EXTERNAL_DB_*` en settings, ver
    # `services/db_source.py`); acá solo se guarda QUÉ objeto de esa base consultar. Vacío (el
    # default de todo dashboard existente) significa que este dashboard sigue alimentándose
    # exclusivamente por carga de Excel — ambas fuentes no son excluyentes en el modelo, pero la
    # UI expone una sola vía a la vez por dashboard.
    fuente_bd_tipo = models.CharField(max_length=20, choices=FuenteBDTipo.choices, blank=True, default='')
    fuente_bd_nombre = models.CharField(max_length=255, blank=True, default='')
    # Parámetros con nombre para un `fuente_bd_tipo='procedimiento'` que los exija (ej.
    # `{"FechaCorte": "2026-07-31"}` para `EXEC dbo.sp_x @FechaCorte = ?`) — solo aplica a
    # procedimientos, una vista se consulta siempre como `SELECT * FROM <vista>` sin parámetros.
    # Los VALORES se bindean como parámetro pyodbc real (nunca interpolados en el SQL, ver
    # `services/db_source.py::leer_fuente`); solo los NOMBRES se validan por regex (van armados en
    # el texto de la consulta como `@nombre = ?`, un identificador no se puede parametrizar).
    fuente_bd_parametros = models.JSONField(default=dict, blank=True)

    class FuenteBDFechaFormato(models.TextChoices):
        """Formato de texto en el que se envía el VALOR de `FechaCorte` al ejecutar el
        procedimiento (`services/db_source.py::leer_fuente`) — el valor en sí siempre se guarda en
        `fuente_bd_parametros` como ISO (`YYYY-MM-DD`, lo único que puede entregar el
        `<input type="date">` del frontend); este catálogo solo decide cómo se reescribe recién al
        armar la consulta, nunca cambia lo guardado — así `services/fuente_bd_scheduler.py::
        avanzar_fecha_corte` (que asume ISO al leer el valor guardado) sigue funcionando sin
        cambios sea cual sea el formato de envío elegido."""
        ISO = 'YYYY-MM-DD', 'AAAA-MM-DD (2026-07-31)'
        DIA_MES_ANIO = 'DD/MM/YYYY', 'DD/MM/AAAA (31/07/2026)'
        MES_DIA_ANIO = 'MM/DD/YYYY', 'MM/DD/AAAA (07/31/2026)'
        ISO_CON_HORA = 'YYYY-MM-DD HH:mm:ss', 'AAAA-MM-DD HH:mm:ss (2026-07-31 00:00:00)'

    # Solo tiene efecto cuando el procedimiento recibe `FechaCorte` (`fuente_bd_parametros` la
    # trae) — vacío/`ISO` (el default) reproduce el comportamiento de siempre. Ver
    # `services/db_source.py::formatear_valor_fecha_corte`.
    fuente_bd_fecha_formato = models.CharField(
        max_length=30, choices=FuenteBDFechaFormato.choices, blank=True, default=FuenteBDFechaFormato.ISO,
    )

    class FuenteBDFrecuencia(models.TextChoices):
        SEMANAL = 'semanal', 'Semanal (todos los domingos)'
        MENSUAL = 'mensual', 'Mensual (mismo día del mes)'

    # Actualización automática opcional de la fuente de base de datos, sin intervención humana —
    # `services/fuente_bd_scheduler.py` (disparado por `manage.py actualizar_fuentes_bd`, sin
    # ningún programador de tareas propio de la app, ver docstring del comando) reconecta y
    # reaplica el ÚLTIMO mapeo/alias confirmados por un humano (`fuente_bd_ultimo_mapeo`/
    # `fuente_bd_ultimo_aliases` abajo) — nunca vuelve a mostrar el asistente de columnas. Vacío
    # (default) significa que este dashboard solo se actualiza cuando alguien hace clic en
    # "Conectar vista de base de datos" a mano.
    fuente_bd_frecuencia_actualizacion = models.CharField(
        max_length=20, choices=FuenteBDFrecuencia.choices, blank=True, default='',
    )
    # Ancla de la recurrencia: el día en que se (re)configuró la frecuencia actual (nunca se toca
    # al reconectar manualmente sin cambiar la frecuencia). "Semanal" solo la usa para saber desde
    # cuándo rige (la ejecución en sí siempre es domingo); "Mensual" toma el día-del-mes de acá
    # para repetir ese mismo número todos los meses (`fuente_bd_scheduler.debe_actualizarse_hoy`).
    fuente_bd_fecha_configuracion = models.DateField(null=True, blank=True)
    # Última vez que la actualización AUTOMÁTICA corrió con éxito para este dashboard — evita
    # correrla dos veces el mismo domingo/día-del-mes si el comando se invoca más de una vez, y es
    # la referencia para saber si "hoy" ya le toca de nuevo.
    fuente_bd_ultima_actualizacion_automatica = models.DateField(null=True, blank=True)
    # Foto del `mapeo`/`aliases` de la ÚLTIMA vez que un humano confirmó "Aplicar a la plantilla"
    # para este dashboard (`views.AplicarMapeoPlantillaView`, cualquiera sea el origen del archivo)
    # — es lo que `fuente_bd_scheduler` reaplica sin intervención en cada actualización automática,
    # así una actualización no puede "romper" un mapeo que un humano ajustó a mano, ni pedirle a
    # nadie que lo repita.
    fuente_bd_ultimo_mapeo = models.JSONField(default=dict, blank=True)
    fuente_bd_ultimo_aliases = models.JSONField(default=dict, blank=True)
    # Congela la ESTRUCTURA del dashboard: no se puede agregar, eliminar, reordenar, redimensionar
    # ni ocultar ningún componente. Los DATOS no se congelan — el mapeo de columnas, el título y
    # los colores se siguen editando normalmente, porque son justamente lo que hay que poder
    # ajustar cuando cambia el origen (ver `services/db_source.py`).
    #
    # Vive acá y no como `config.bloqueado` en cada componente (el mecanismo anterior, que sigue
    # vigente para la plantilla base) por dos motivos: "no agregar componentes nuevos" no es una
    # propiedad de ningún componente existente, y una marca por componente se pierde en cuanto se
    # vuelve a sembrar el dashboard, que reescribe la lista entera.
    #
    # Un superusuario puede saltear el bloqueo operación por operación confirmando su contraseña
    # (`services/desbloqueo.py`); para todos los demás es infranqueable desde la aplicación.
    estructura_bloqueada = models.BooleanField(default=False)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # Pestañas dentro de un mismo dashboard: cada pestaña es un `Dashboard` más (su propia
    # plantilla de 13 posiciones, su propio archivo cargado — completamente independiente),
    # enlazado a la raíz de la familia por este campo. La raíz misma tiene `parent=None` y
    # `orden=1`; sus pestañas (`raiz.pestanas`) toman `orden` 2..5 (máximo 5 por familia, ver
    # `services/dashboards.py::crear_pestana`). `on_delete=CASCADE`: borrar la raíz borra sus
    # pestañas (`services/dashboards.py::eliminar_dashboard` limpia antes los datos de cada una).
    parent = models.ForeignKey('self', null=True, blank=True, related_name='pestanas', on_delete=models.CASCADE)
    orden = models.PositiveIntegerField(default=1)

    # Control de acceso por dashboard (roles editores/lectores + dueño). `owner` nace igual a
    # `created_by` (ver `services/dashboards.py::crear_dashboard`) pero es reasignable después por
    # un superusuario — a diferencia de `created_by`, que es un hecho histórico inmutable. Un
    # dashboard sin ningún rol en `roles_editores`/`roles_lectores` (el caso de todos los
    # dashboards existentes hoy y el default de cualquiera nuevo) no tiene ACL activa: se sigue
    # autorizando por el permiso global de siempre (`cartera/permisos.py::tiene_acceso_dashboard`).
    # En cuanto tiene al menos un rol asignado en cualquiera de los dos grupos, el acceso queda
    # restringido a: el dueño, el superusuario, o quien tenga uno de esos roles — `roles_editores`
    # puede ver y editar, `roles_lectores` solo puede ver.
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='dashboards_propios',
    )
    roles_editores = models.ManyToManyField(Group, blank=True, related_name='dashboards_como_editor')
    roles_lectores = models.ManyToManyField(Group, blank=True, related_name='dashboards_como_lector')

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
    # Quién subió el archivo (`ValidarArchivoView.post`, siempre autenticado —
    # `DEFAULT_PERMISSION_CLASSES=[IsAuthenticated]`). `SET_NULL`: borrar el usuario no debe borrar
    # el historial de cargas, solo perder la referencia (mismo criterio que `Dashboard.created_by`).
    subido_por = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='cargas_archivo',
    )
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
    # Copia permanente (dentro de `CARTERA_ARCHIVOS_DIR`, no sujeta a la limpieza de 24h de
    # `archivo_temp_nombre`) del archivo ya renombrado por alias, escrita al aplicar la plantilla
    # (`views._guardar_archivo_permanente`) — permite reconfigurar el mapeo de columnas de un
    # componente después, desde "Configurar componente", sin volver a cargar el archivo.
    archivo_permanente_nombre = models.CharField(max_length=255, blank=True, default='')

    # Si esta carga cuenta para la comparación histórica del dashboard (Tabla 3 y "Histórico de
    # cargas", ver `services/historico.py::calcular_tabla_historica`) — editable desde "Histórico
    # de cargas" (checkbox por carga, persiste de inmediato). `default=True`: toda carga cuenta por
    # defecto, igual que el comportamiento antes de que este campo existiera. No borra
    # `FilaArchivoHistorico`: los datos siguen guardados, solo se excluyen del cálculo mientras esté
    # en `False`, así se puede revertir sin perder nada.
    incluir_en_historico = models.BooleanField(default=True)

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


class FilaArchivoHistorico(models.Model):
    """Fila de un archivo cargado, guardada al aplicar el mapeo de la plantilla
    (`AplicarMapeoPlantillaView`) — permite armar tablas históricas (sección 28) comparando varias
    cargas del mismo dashboard a través del tiempo, sin depender de que el archivo físico original
    siga existiendo en disco. No asume ningún esquema fijo de columnas (a diferencia de
    `RegistroCartera`, pensado solo para el dominio clásico de cartera): cada fila es un JSON con
    los pares columna→valor ya renombrados por alias, iguales a los que ve el mapeo de columnas.
    `on_delete=CASCADE`: borrar la carga borra sus filas históricas."""

    carga = models.ForeignKey(CargaArchivo, related_name='filas_historicas', on_delete=models.CASCADE)
    orden = models.PositiveIntegerField()  # posición original en el archivo, para reconstruir el orden
    datos = models.JSONField(encoder=DjangoJSONEncoder)  # encoder: serializa fechas/Decimal sin fricción

    class Meta:
        ordering = ['carga', 'orden']

    def __str__(self):
        return f'{self.carga_id} fila {self.orden}'


class ColumnaHistorica(models.Model):
    """Columna marcada por el usuario como "histórica" en el paso "Renombrar columnas" (casilla
    junto a cada columna) — persiste por `dashboard_id` para reconocerla sola en la próxima carga
    del mismo dashboard, sin que el usuario tenga que volver a tildarla. Decide tanto qué columnas
    persisten en `FilaArchivoHistorico` de acá en adelante (solo estas, no la fila completa) como
    qué columnas compara automáticamente Tabla 3 (`TablaHistoricaAutomatica`, frontend).
    `columna` ya viene renombrada por alias, igual que `FilaArchivoHistorico.datos`."""

    dashboard_id = models.SlugField(max_length=100, db_index=True)
    columna = models.CharField(max_length=200)

    class Meta:
        unique_together = [('dashboard_id', 'columna')]
        ordering = ['dashboard_id', 'columna']

    def __str__(self):
        return f'{self.dashboard_id}: {self.columna}'


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
    # Propuesta de mapeo (columna(s), tipo de cálculo/gráfico, filtro) que produjo `content` — solo
    # tiene sentido para las 15 posiciones fijas de la plantilla (`services/plantilla.py`), pero se
    # modela acá de forma genérica (vacío en cualquier otro componente) para no acoplar este modelo
    # a esa plantilla. Permite reabrir "Configurar componente" y seguir editando esos mismos datos
    # más adelante, en vez de que el mapeo se pierda apenas se aplica.
    mapeo = models.JSONField(default=dict, blank=True)

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
