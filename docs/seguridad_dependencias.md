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

### Vulnerabilidades de npm corregidas

- `vitest` 4.1.10 → 4.1.11: recorrido de rutas en `@vitest/mocker`. Solo desarrollo.
- `nanoid` 3.3.16 → 3.3.19 (vía `vite` → `postcss`): bucle infinito con tamaño cero. Solo build.

Ninguna de las dos llegaba al paquete que se sirve a los usuarios.

## Pendiente de decisión

### Pillow 10.4 (de 2024), y parsea lo que suben los usuarios

`Pillow>=10.4,<10.5`, con la 12.3 disponible. Importa más que otras dependencias viejas porque es
lo que valida los avatares: `AvatarUploadSerializer` (`apps/authentication/serializers.py`) usa
`ImageField`, que abre con Pillow el archivo que sube cualquier usuario autenticado. Es la única
biblioteca del backend que procesa un binario controlado por el usuario, y el historial de CVE de
Pillow está casi todo en el parseo de imágenes.

Actualizar dentro de la serie 10.x no alcanza; hay que ampliar el rango.

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
