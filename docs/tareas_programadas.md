# Tareas programadas

El proyecto tiene dos comandos que deben correr solos, todos los días. Estaban escritos y probados,
pero nada los invocaba: se decidió explícitamente no llevar un programador dentro de la aplicación
(ver el `help` de `actualizar_fuentes_bd`) y delegar en el del sistema operativo. Este documento es
esa delegación.

| Comando | Qué hace | Si no corre |
|---|---|---|
| `actualizar_fuentes_bd` | Reconecta y reaplica el último mapeo confirmado a cada dashboard conectado a una vista o procedimiento cuya frecuencia venza hoy | La pantalla ofrece frecuencia semanal/mensual y muestra "Próxima actualización automática", pero los datos nunca se actualizan solos |
| `clean_temp_uploads --horas 24` | Borra los archivos temporales de carga de más de 24 h que ninguna `CargaArchivo` siga referenciando | Los temporales se acumulan sin límite |

Los dos son seguros de ejecutar cualquier día: `actualizar_fuentes_bd` decide por su cuenta a qué
dashboards les toca hoy (un martes no hace nada), y `clean_temp_uploads` nunca borra un archivo que
una carga todavía referencia.

## Instalación (Windows)

Desde PowerShell **como administrador**:

```powershell
cd C:\ruta\al\repo\backend\scripts
.\programar_tareas.ps1
```

Registra dos tareas diarias: la actualización a las 03:00 y la limpieza a las 03:30. Para otra
hora, `.\programar_tareas.ps1 -Hora 02:15`. Para quitarlas, `.\programar_tareas.ps1 -Quitar`.

Verificar sin esperar a mañana:

```powershell
Start-ScheduledTask -TaskName 'CMS Dashboards - actualizar fuentes BD'
Get-ScheduledTaskInfo -TaskName 'CMS Dashboards - actualizar fuentes BD'
```

## Registro

Todo queda en `backend\logs\tareas\<comando>-<año>-<mes>.log` (ignorado por git), un archivo por
comando y por mes:

```
===== 2026-09-11 12:23:11 — manage.py clean_temp_uploads --horas 24
11630 archivo(s) temporal(es) eliminado(s). 30 conservado(s) por seguir referenciados por una carga.
----- OK en 5s
```

El registro no es un adorno: una tarea programada que falla lo hace en silencio, y sin log nadie se
entera hasta que alguien nota que los datos están viejos. El envoltorio además devuelve el código de
salida del comando, así que un fallo también se ve en el historial del propio Programador de tareas.

## En otro sistema operativo

`tarea_programada.ps1` es específico de Windows. El equivalente en cron, corriendo a la misma hora:

```cron
0 3 * * * cd /ruta/al/repo/backend && .venv/bin/python manage.py actualizar_fuentes_bd >> logs/tareas/actualizar_fuentes_bd.log 2>&1
30 3 * * * cd /ruta/al/repo/backend && .venv/bin/python manage.py clean_temp_uploads --horas 24 >> logs/tareas/clean_temp_uploads.log 2>&1
```

## Limitación conocida: una corrida perdida pierde el período entero

`debe_actualizarse_hoy` pregunta "¿hoy es el día?", no "¿está atrasado?". Para la frecuencia semanal
el día es el domingo; para la mensual, el día ancla del mes.

La consecuencia, comprobada: con la última actualización el domingo 9 y el servidor apagado el
domingo 16, el comando devuelve `False` el lunes 17, el miércoles 19 y el sábado 22 — el dashboard
llega al sábado con **13 días** sin actualizar y nadie reintenta. Con frecuencia mensual se pierde
un mes.

`-StartWhenAvailable` (ya activado en `programar_tareas.ps1`) cubre el caso más común: si la máquina
está apagada a las 03:00 pero se enciende ese mismo día, Windows corre la tarea igual. Lo que no
cubre es un día calendario entero sin encender la máquina.

Resolverlo de verdad requiere cambiar el criterio a "vencido" en vez de "es hoy" —comparar contra
`fuente_bd_ultima_actualizacion_automatica` y disparar si ya pasó la fecha objetivo—, lo que cambia
un comportamiento visible ("se actualiza los domingos") y merece decidirse aparte.
