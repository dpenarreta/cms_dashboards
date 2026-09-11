# Dependencias y vulnerabilidades conocidas

Estado al 11/09/2026, tras la primera revisión de dependencias del proyecto. `.github/dependabot.yml`
mantiene esto vigente de acá en más: revisa semanalmente contra la base de avisos de GitHub y abre
un PR cuando aparece una versión que corrige algo.

## Aplicado

### Django 5.0 → 5.2 LTS (11/09/2026)

La serie 5.0 había dejado de recibir parches de seguridad. Se pasó a **5.2 LTS** (soporte hasta
abril de 2028) y no a 6.x: el objetivo era volver a una serie soportada con el menor salto posible.

El salto arrastró tres dependencias que declaran compatibilidad por serie de Django:

| Paquete | De | A | Por qué |
|---|---|---|---|
| `Django` | 5.0.14 | 5.2.17 | La serie 5.0 ya no recibe parches |
| `djangorestframework` | 3.15.2 | 3.18.1 | 3.18 exige `django>=5.2`; quedan acopladas a propósito |
| `mssql-django` | 1.5 | 1.8.0 | <1.6 no soporta Django 5.1+; 1.8 es la primera serie que declara 5.2 |
| `django-cors-headers` | 4.4.0 | 4.9.0 | 4.4 es anterior a la compatibilidad declarada con 5.2 |

Qué se verificó antes de aplicarlo: ninguna de las APIs removidas en 5.1 ni en 5.2 está en uso
(`index_together`, `DEFAULT_FILE_STORAGE`/`STATICFILES_STORAGE`, `get_storage_class()`,
`make_random_password()`, `assertFormsetError`, los hashers SHA1/MD5, los campos `CI*` de postgres,
`length_is`). El único punto de contacto con un cambio de 5.2 es el envío de correo, y ya usaba
`attach_alternative()`, que es justamente el camino que 5.2 dejó como único soportado.

Qué se verificó después: las 965 pruebas pasan contra SQL Server **y** contra SQLite con
`DEBUG=False` (las dos configuraciones, la local y la de CI), `check --deploy --fail-level WARNING`
limpio, `makemigrations --check` sin cambios, y **cero advertencias de deprecación** — o sea que el
próximo salto de serie tampoco arrastra deuda acumulada. Verificado además en el navegador: login,
lista de dashboards y un dashboard con KPIs y gráficos.

De paso se corrigió una deriva: `argon2-cffi` estaba fijado en `>=23.1,<23.2` pero el entorno local
tenía la 25.1.0 instalada. O sea que la CI y cualquier entorno nuevo instalaban una versión más
vieja que la que se venía usando para desarrollar. El rango pasó a `>=23.1,<26`.

### Pillow 10.4 → 12.3 (11/09/2026)

Pillow es la única biblioteca del backend que parsea un binario controlado por el usuario: los
avatares, vía el `ImageField` de Django (`AvatarUploadSerializer`, `apps/authentication/serializers.py`).
La 10.4 arrastraba **12 avisos de seguridad, 9 de severidad alta**, todos corregidos en 12.3.

Por qué era alcanzable de verdad, y no una lista teórica: se comprobó que **Pillow despacha por la
firma binaria del contenido, no por la extensión del nombre**. Un archivo llamado `avatar.png` cuyo
contenido es un GIF se acepta, y lo procesa `GifImagePlugin`. La validación de extensión de Django
(`validate_image_file_extension`) corre *después* de `Image.open()`, así que no funciona como filtro
previo: basta nombrar el archivo `.png` para llegar a cualquier plugin de formato de Pillow.

Eso pone al alcance de cualquier usuario autenticado los parsers donde estaban los fallos graves:
escritura fuera de límites en PSD (CVE-2026-25990, CVE-2026-42311), bombas de descompresión en FITS
y GD (CVE-2026-40192, CVE-2026-55380), lectura fuera de límites en la ruta mmap (CVE-2026-54058) y
denegación de servicio en JPEG2000 (CVE-2026-59204). Los avisos restantes son de fuentes y de
`ImageCms`, que este proyecto no usa.

El salto cruza dos versiones mayores, pero el riesgo de ruptura era bajo y se verificó: el único uso
directo de Pillow en todo el repo es `Image.new(...).save(buffer, format='PNG')` en una prueba. En
producción solo se lo alcanza a través del `ImageField` de Django (`Image.open()` + `verify()`), API
que no cambió. Ninguna de las APIs removidas en 11.0 ni en 12.0 está en uso (`PyAccess`,
`USE_CFFI_ACCESS`, `IFD_LEGACY_API`, `PSFile`, `raise_oserror()`, `ImageCms`, `IptcImageFile`, los
modos BGR, el parámetro `hints` de `getdraw()`). Python 3.12 supera el mínimo de 3.10 que pide la 12.

Verificación: las 965 pruebas pasan contra SQL Server y contra SQLite con `DEBUG=False`, incluidas
las de `apps.authentication` que ejercen la subida de avatar de punta a punta — subida exitosa,
rechazo de un archivo que no es imagen, y borrado del avatar anterior del disco.

### Vulnerabilidades de npm corregidas

- `vitest` 4.1.10 → 4.1.11: recorrido de rutas en `@vitest/mocker`. Solo desarrollo.
- `nanoid` 3.3.16 → 3.3.19 (vía `vite` → `postcss`): bucle infinito con tamaño cero. Solo build.

Ninguna de las dos llegaba al paquete que se sirve a los usuarios.

## Pendiente de decisión

### quill 2.0.3: XSS sin corrección disponible

`react-quill-new` (el editor de texto enriquecido de las plantillas de correo) depende de
`quill ~2.0.3`, y 2.0.3 tiene un XSS reportado en la exportación a HTML. **2.0.3 es la última
versión que existe: no hay corrección upstream.**

`npm audit fix --force` propone bajar a `react-quill-new@3.7.0`, que depende de `quill ~2.0.2`.
Eso NO corrige nada: 2.0.2 es anterior y queda fuera del rango del aviso solo por cómo se declaró.
Sería perder mejoras reales a cambio de que la herramienta deje de avisar. **No lo hagas.**

Exposición real en este proyecto: el editor solo lo abre quien tiene `configuracion.editar`, y el
HTML guardado ya se trata como confiado por diseño (ver `EmailTemplate` en
`apps/authentication/models.py`, que razona explícitamente sobre esto). El escenario sería que
alguien con ese permiso guarde HTML malicioso y se ejecute en el navegador del próximo
administrador que abra la pantalla — es decir, requiere un permiso que ya otorga control sobre la
identidad visual y las plantillas de correo.

Opciones, en orden de costo: dejarlo documentado y seguir el aviso por si aparece una versión
corregida; o sanear `html_body` en el backend con una lista blanca al guardar, lo que agrega
defensa en profundidad pero puede romper plantillas legítimas con estilos en línea.
