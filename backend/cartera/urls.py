from django.urls import path

from . import views

urlpatterns = [
    path('validar-archivo', views.ValidarArchivoView.as_view(), name='validar-archivo'),
    path('analizar-columnas', views.AnalizarColumnasView.as_view(), name='analizar-columnas'),
    path('recomendar-graficas', views.RecomendarGraficasView.as_view(), name='recomendar-graficas'),
    path('agregar-grafica', views.AgregarGraficaView.as_view(), name='agregar-grafica'),
    path('procesar', views.ProcesarView.as_view(), name='procesar'),
    path('resumen/<uuid:carga_id>', views.ResumenView.as_view(), name='resumen'),
    path('top-clientes/<uuid:carga_id>', views.TopClientesView.as_view(), name='top-clientes'),
    path('pareto-ciudades/<uuid:carga_id>', views.ParetoCiudadesView.as_view(), name='pareto-ciudades'),
    path('recuperadores/<uuid:carga_id>', views.RecuperadoresView.as_view(), name='recuperadores'),
    path('causales/<uuid:carga_id>', views.CausalesView.as_view(), name='causales'),
    path('recuperadores-causales/<uuid:carga_id>', views.RecuperadoresCausalesView.as_view(), name='recuperadores-causales'),
    path('detalle/<uuid:carga_id>', views.DetalleView.as_view(), name='detalle'),
    path('exportar/<uuid:carga_id>', views.ExportarView.as_view(), name='exportar'),
    path('archivo/<uuid:carga_id>', views.ArchivoView.as_view(), name='archivo'),
]
