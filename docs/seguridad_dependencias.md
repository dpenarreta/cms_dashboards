# Dependencias y vulnerabilidades conocidas

Estado al 11/09/2026, tras la primera revisión de dependencias del proyecto. `.github/dependabot.yml`
mantiene esto vigente de acá en más: revisa semanalmente contra la base de avisos de GitHub y abre
un PR cuando aparece una versión que corrige algo.

## Pendiente de decisión

### Django 5.0 está fuera de soporte

`requirements.txt` fija `Django>=5.0,<5.1` y hay instalada la 5.0.14. La serie 5.0 dejó de recibir
parches de seguridad; las series con soporte hoy son 6.1, 6.0 y 5.2 LTS.

Es el hallazgo más importante de esta revisión: **no es una vulnerabilidad puntual, es la ausencia
de parches**. Cualquier fallo de seguridad que Django corrija de ahora en adelante no llega a este
proyecto mientras el rango siga fijado ahí.

Dependabot no lo va a proponer solo, porque respeta el rango `<5.1`. Hay que ampliarlo a mano.
La ruta de menor riesgo es 5.0 → 5.2 LTS (soporte extendido, menos cambios incompatibles que
saltar a 6.x). Requiere leer las notas de versión de 5.1 y 5.2 y correr la suite.

### Pillow 10.4 (de 2024), y parsea lo que suben los usuarios

`Pillow>=10.4,<10.5`, con la 12.3 disponible. Importa más que otras dependencias viejas porque es
lo que valida los avatares: `AvatarUploadSerializer` (`apps/authentication/serializers.py`) usa
`ImageField`, que abre con Pillow el
archivo que sube cualquier usuario autenticado. Es la única biblioteca del backend que procesa un
binario controlado por el usuario, y el historial de CVE de Pillow está casi todo en el parseo de
imágenes.

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

## Corregido en esta revisión

- `vitest` 4.1.10 → 4.1.11: recorrido de rutas en `@vitest/mocker`. Solo desarrollo.
- `nanoid` 3.3.16 → 3.3.19 (vía `vite` → `postcss`): bucle infinito con tamaño cero. Solo build.

Ninguna de las dos llegaba al paquete que se sirve a los usuarios.
