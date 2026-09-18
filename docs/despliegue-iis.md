# Publicación en IIS — servidor de aplicaciones 10.0.2.33

Cómo queda montado, y qué hacer para publicar y para actualizar.

## La forma

```
  <sitio IIS>/          ->  frontend compilado (Vite)      archivos estáticos
  <sitio IIS>/api       ->  aplicación IIS con el backend  HttpPlatformHandler -> waitress -> Django
  <sitio IIS>/media     ->  directorio virtual             archivos subidos
```

Todo en **un solo origen**. No es un detalle estético: la cookie del token de refresco es
`SameSite=Lax`, que solo viaja si el frontend y la API comparten origen. Separarlos obliga a
`SameSite=None`, y eso **exige HTTPS** — que hoy no hay.

### Por qué HttpPlatformHandler y no ARR

IIS no ejecuta Python por sí mismo; hace falta un puente. Las dos opciones habituales:

| | |
|---|---|
| **HttpPlatformHandler** (el elegido) | Un módulo. IIS arranca el proceso de Python, le asigna un puerto y le reenvía las peticiones. El proceso vive y muere con el sitio |
| ARR + URL Rewrite | Dos módulos, y el proceso de Python queda por fuera: hay que instalarlo como servicio aparte, arrancarlo y vigilarlo |

Con el primero, reiniciar la aplicación es reiniciar el grupo de aplicaciones. Sin servicios sueltos
que alguien tenga que acordarse de levantar después de un reinicio del servidor.

### Por qué waitress y no gunicorn

gunicorn **no corre en Windows**: depende de `fcntl`, que es de Unix. waitress es puro Python,
multihilo y sin dependencias nativas. Ya está en `requirements.txt`.

## Requisitos en el servidor

`publicar.ps1` los verifica antes de tocar nada y se detiene con el enlace de descarga si falta alguno.

| | Cómo se comprueba |
|---|---|
| IIS con `WebAdministration` | `Import-Module WebAdministration` |
| [HttpPlatformHandler 1.2](https://www.iis.net/downloads/microsoft/httpplatformhandler) | Aparece en los módulos globales de IIS |
| [URL Rewrite 2.1](https://www.iis.net/downloads/microsoft/url-rewrite) | Ídem |
| Python 3.12, instalado para todos los usuarios | `python --version` |
| ODBC Driver 17 for SQL Server | `Get-OdbcDriver` |

Node **no** hace falta en el servidor: el frontend se compila antes y se copia ya compilado.

## Publicar

1. **Compilar el frontend** (donde haya Node — tu máquina sirve):

   ```powershell
   cd frontend
   npm ci
   npm run build
   ```

   `VITE_API_BASE_URL` queda vacía: al servirse todo desde el mismo origen, las llamadas van a
   `/api` relativo. Si alguna vez la API vive en otro host, hay que definirla **antes** del build —
   Vite la hornea en el bundle y después no se cambia.

2. **Copiar el repositorio al servidor**, con `frontend\dist` y `deploy\.env.produccion` incluidos.

3. **Ejecutar en el servidor**, en PowerShell **como administrador**:

   ```powershell
   cd <repo>\deploy\iis
   .\publicar.ps1 -Origen <repo> -AbrirFirewall
   ```

   El sitio queda en **`http://10.0.2.33:50810`**. El puerto 80 está ocupado por otro sitio, por eso
   el 50810 es el valor por defecto del script.

   `-AbrirFirewall` crea la regla de entrada para ese puerto (perfiles Dominio y Privado). Sin ella
   el sitio responde desde el propio servidor pero no desde la red, que es un síntoma fácil de
   confundir con un problema de IIS.

### El puerto 50810 necesita reservarse

El rango de puertos dinámicos de Windows arranca en **49152**, así que 50810 cae dentro: el sistema
puede asignárselo a una conexión saliente efímera antes de que IIS lo tome. El síntoma es
desconcertante — el sitio anda, se reinicia el servidor, y no vuelve a levantar porque "el puerto
está en uso" — y aparece de forma intermitente.

`publicar.ps1` lo detecta y lo reserva solo:

```powershell
netsh int ipv4 add excludedportrange protocol=tcp startport=50810 numberofports=1
```

Si la reserva falla (solo se puede hacer con el puerto libre), el script avisa y sigue: la
aplicación funciona igual, pero conviene resolverlo antes del primer reinicio.

El script copia el código, crea el entorno virtual, instala dependencias, genera los `web.config`
con las rutas reales, crea el sitio, la aplicación `/api` y el directorio virtual `/media`, da
permisos de escritura sobre `media\` y `logs\` a la identidad del grupo de aplicaciones, restringe
el `.env`, y al final comprueba que el frontend y la API respondan.

## Actualizar

```powershell
.\publicar.ps1 -Origen <repo> -SoloCodigo
```

Copia código y configuración sin tocar IIS ni reinstalar dependencias. Si la versión nueva trae
migraciones o dependencias, correrlo sin `-SoloCodigo`.

La copia **preserva** `media\`, `logs\`, `.venv\` y el `.env` del servidor: se excluyen
explícitamente del espejado, porque viven en el destino y no en el repositorio. Sin esas
exclusiones, cada despliegue borraría los archivos cargados por los usuarios.

## Dónde mirar cuando algo falla

| Síntoma | Dónde |
|---|---|
| La API devuelve 404 | `/api` no está enrutando al backend: revisar que la aplicación exista en IIS |
| La API devuelve 502 o 503 | El proceso de Python no arrancó. **El log está en `<destino>\logs\backend*.log`** — lo escribe HttpPlatformHandler con la salida del proceso |
| Cualquier ruta devuelve el HTML del SPA | La regla de reescritura no está excluyendo `/api`: revisar el `web.config` del frontend |
| 400 en todas las peticiones | `ALLOWED_HOSTS` no incluye el host con el que se accede (va sin puerto: `10.0.2.33`) |
| Bucle de redirecciones | `SECURE_SSL_REDIRECT` quedó en `True` sin HTTPS |

El log del backend es lo primero que hay que mirar: como el proceso lo administra IIS, un fallo al
arrancar (una variable mal puesta, la base inalcanzable) no se ve en el navegador, que solo muestra
un 502 genérico.

## Después de publicar

- **Sembrar el Directorio de Cartera**, que no viene en el esquema:

  ```powershell
  cd <destino>\backend
  .venv\Scripts\python.exe manage.py sembrar_directorio_cartera
  ```

- **Registrar las tareas programadas** (`docs/tareas_programadas.md`): sin ellas, los dashboards
  conectados a una fuente de base de datos no se actualizan solos. En un servidor hay que
  registrarlas con S4U para que corran sin sesión iniciada.

- **HTTPS**: cuando haya certificado, agregar el binding y borrar las tres líneas provisorias del
  `.env` (`SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`, `REFRESH_COOKIE_SECURE`). Los valores por
  defecto del código ya son los seguros.
