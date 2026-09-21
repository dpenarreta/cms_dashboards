"""Diagnóstico de SOLO LECTURA sobre los metadatos de la base de origen: dónde vive el RUC."""
import django, os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()
import pandas as pd
from cartera.services import db_source

conn = db_source._conectar()
try:
    consulta = """
        SELECT TABLE_SCHEMA, TABLE_NAME, COLUMN_NAME, DATA_TYPE
          FROM INFORMATION_SCHEMA.COLUMNS
         WHERE COLUMN_NAME LIKE '%ruc%' OR COLUMN_NAME LIKE '%ident%'
            OR COLUMN_NAME LIKE '%cedula%' OR COLUMN_NAME LIKE '%Codigo%cli%'
         ORDER BY TABLE_NAME, COLUMN_NAME
    """
    df = pd.read_sql(consulta, conn)
    print(f'{len(df)} columna(s) candidatas en la base de origen:')
    print(df.head(25).to_string(index=False))
finally:
    conn.close()
