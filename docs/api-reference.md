# Referencia de API — Dashboard de Cartera

Todos los endpoints están bajo `/api/cartera/`. No hay autenticación (ver limitaciones en el
`README.md`); cualquier request con un `carga_id` válido puede consultarlo.

## Carga y procesamiento

| Método | Ruta | Descripción |
|---|---|---|
| POST | `/validar-archivo` | Sube un Excel, detecta hojas/encabezados y sugiere el mapeo de columnas. |
| POST | `/procesar` | Aplica el mapeo confirmado, inserta los registros en SQL Server y devuelve los KPIs. |
| DELETE | `/archivo/<carga_id>` | Elimina la carga y sus registros. |

## Consulta y agregaciones

| Método | Ruta | Devuelve |
|---|---|---|
| GET | `/resumen/<carga_id>` | KPIs (sección 9 del dashboard original). |
| GET | `/top-clientes/<carga_id>` | Lista de los 10 clientes con mayor saldo. |
| GET | `/pareto-ciudades/<carga_id>` | Cartera vencida por ciudad — ver forma de respuesta abajo. |
| GET | `/recuperadores/<carga_id>` | Saldo por recuperador. |
| GET | `/causales/<carga_id>` | Cartera por causal. |
| GET | `/recuperadores-causales/<carga_id>` | Cruce recuperador × causal (`chart` y `matriz`). |
| GET | `/detalle/<carga_id>` | Documentos paginados. |
| GET | `/exportar/<carga_id>` | Descarga Excel/CSV. |

### Query params comunes (todos los GET de agregación y `/detalle`)

| Parámetro | Tipo | Notas |
|---|---|---|
| `fecha_corte` | `YYYY-MM-DD` | Si se omite, usa la fecha de corte de la carga. |
| `cliente` | texto | Coincidencia parcial (`icontains`) sobre nombre o RUC. |
| `ciudad`, `zona`, `sucursal`, `recuperador`, `causal`, `producto`, `articulo`, `tipo_venta`, `estado_cliente` | texto | Coincidencia exacta insensible a mayúsculas. **Acepta una lista separada por comas** (`ciudad=QUITO,CUENCA`) para "cualquiera de estos" — así es como el drill-down de "Otras ciudades"/"OTRAS" abre el detalle de varias categorías agrupadas a la vez. |
| `estado_cartera` | `VENCIDA` \| `NO VENCIDA` \| `SIN FECHA DE VENCIMIENTO` \| `SALDO CERO` \| `SALDO A FAVOR` | Se calcula dinámicamente según `fecha_corte`, no es una columna de la base. |
| `rango_mora` | uno de los 9 rangos fijos (`POR VENCER`, `0-30 DÍAS`, …, `SIN FECHA`) | Igual que `estado_cartera`, calculado dinámicamente. |
| `dias_vencidos_min`, `dias_vencidos_max` | número | **Nuevo.** Filtra por días vencidos calculados (`fecha_corte - fecha_vencimiento`), inclusive. Lo usan las tarjetas KPI "> 120 días" / "> 360 días" (`dias_vencidos_min=121` / `361`) para abrir un rango abierto que no corresponde a un único bucket de `rango_mora`. |

Solo se leen los parámetros de esta lista — cualquier otro query param se ignora silenciosamente
(no se construye SQL dinámico a partir de nombres de columna arbitrarios).

### `/detalle/<carga_id>` — adicionales

| Parámetro | Notas |
|---|---|
| `page`, `page_size` | Paginación (`page_size` máx. 1000). |
| `buscar` | Búsqueda en cliente, RUC o número de documento. |
| `ordering` | Nombre de columna, prefijo `-` para descendente. |

Respuesta:

```json
{
  "count": 13,
  "page": 1,
  "page_size": 50,
  "saldo_filtrado": 7401.25,
  "porcentaje_sobre_cartera_total": 99.33,
  "fecha_corte": "2026-06-30",
  "results": [ { "cliente": "...", "saldo": 500.0, "estado_calculado": "VENCIDA", "...": "..." } ]
}
```

### `/pareto-ciudades/<carga_id>` — forma de respuesta (cambiada por el gráfico de pastel)

Antes devolvía una lista plana (usada por el gráfico de Pareto, ya eliminado). Ahora devuelve:

```json
{
  "total_vencida": 302687.53,
  "ciudades": [
    { "ciudad": "QUITO", "saldo_vencido": 181157.46, "porcentaje": 59.85, "porcentaje_acumulado": 59.85, "documentos": 434, "clientes": 245 }
  ],
  "ciudades_agrupadas": [
    "...top 8 ciudades...",
    {
      "ciudad": "OTRAS CIUDADES", "saldo_vencido": 1234.0, "porcentaje": 2.1,
      "documentos": 5, "clientes": 3, "ciudades_incluidas": ["LOJA", "MANTA"]
    }
  ]
}
```

`ciudades_agrupadas` solo aparece si hay más de 8 ciudades con cartera vencida; el frontend usa
`ciudades_incluidas` para construir el filtro multivalor (`ciudad=LOJA,MANTA`) al seleccionar
"Otras ciudades". `porcentaje_acumulado` se mantiene en la respuesta por compatibilidad, aunque
el gráfico de pastel ya no lo usa.

### `/causales/<carga_id>` — misma extensión

Cuando hay más de 8 causales, agrega `causales_agrupadas` con una entrada `OTRAS` que incluye
`causales_incluidas` (lista de nombres agrupados), con el mismo propósito que `ciudades_incluidas`.

## Seguridad de los filtros

- Todos los filtros de texto se aplican vía ORM (`filter(**{...})`), nunca SQL crudo.
- El multivalor (`ciudad=A,B,C`) se traduce a `.filter(ciudad__in=[...])`, sigue sin construir SQL a mano.
- `dias_vencidos_min`/`max` se aplican sobre el DataFrame ya anotado (no son columnas reales), y se
  castean con `float()` — un valor no numérico produce un error 500 controlado, no una inyección.
- No existen endpoints que acepten una cláusula de filtro arbitraria; la lista de parámetros
  reconocidos es fija (`cartera/services/filters.py`).
