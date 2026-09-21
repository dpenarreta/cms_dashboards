import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from cartera.models import CargaArchivo, Dashboard, DashboardComponent

ID = 'dashboard-directorio'
d = Dashboard.objects.get(dashboard_id=ID)
print('bloqueado:', d.estructura_bloqueada, '| foto:', len(d.estructura_fijada or []), 'componentes')
print('fuente:', d.fuente_bd_tipo, d.fuente_bd_nombre, d.fuente_bd_parametros)
print()
for c in CargaArchivo.objects.filter(dashboard_id=ID).order_by('-fecha_carga')[:3]:
    print(f'carga {c.fecha_carga:%Y-%m-%d %H:%M}  {c.estado:10} corte={c.fecha_corte} filas={c.total_filas_excel} perm={bool(c.archivo_permanente_nombre)}')
print()
for c in DashboardComponent.objects.filter(layout__dashboard_id=ID, is_visible=True).order_by('order'):
    cont = c.content or {}
    tiene = 'valor' in cont or 'categorias' in cont or 'filas' in cont
    print(f'{c.component_id:32} con_datos={tiene}  con_mapeo={bool(c.mapeo)}  titulo={bool(cont.get("titulo"))}')
