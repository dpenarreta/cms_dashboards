import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
from cartera.models import DashboardComponent
from cartera.services import consulta_deudor

comp = DashboardComponent.objects.get(layout__dashboard_id='dashboard-directorio', component_id='consulta-deudor')
print('mapeo del componente:', {k: v for k, v in (comp.mapeo or {}).items() if k.startswith('columna')})

df, _ = consulta_deudor._df_de('dashboard-directorio')
print()
print('columnas del origen:', list(df.columns))
candidatas = [c for c in df.columns if any(p in str(c).lower() for p in ('ruc', 'ident', 'cedula', 'cédula', 'codigo', 'código', 'nit'))]
print('columnas que podrían servir de identificador:', candidatas or '(ninguna)')
