# Preferencias globales (propuesta)

No se encontró `~/.claude/CLAUDE.md` existente. Este archivo es una propuesta — modificar la
configuración global del usuario afecta a todos sus proyectos, no solo a este repositorio, así
que se deja para que el usuario la copie manualmente en vez de escribirla directamente.

**Copiar el contenido de abajo (a partir de `---`) a**: `~/.claude/CLAUDE.md`
(en Windows: `C:\Users\<usuario>\.claude\CLAUDE.md`)

Solo se incluyen preferencias con evidencia directa en esta sesión. Los campos típicos de un
`CLAUDE.md` global que NO se pudieron confirmar (editor, gestor de paquetes preferido en
proyectos nuevos, convención de commits personal fuera de este repo) se dejan fuera a propósito
— agrégalos manualmente si aplican a todos tus proyectos, no solo a este.

---

# Preferencias globales

## Idioma y comunicación
- Responde siempre en español, incluida la explicación de cambios de código.
- Mantén la ortografía completa del español (tildes, ñ, signos de apertura ¿¡).

## Entorno habitual
- Sistema operativo: Windows 11.
- Shell principal: PowerShell 5.1. También usa Git Bash (sintaxis POSIX) cuando la herramienta lo
  requiere — no asumas sintaxis de PowerShell en un contexto Bash ni viceversa.

## Forma de trabajar
- Antes de una acción destructiva o difícil de revertir (reset --hard, force-push, eliminar
  archivos no creados en la sesión), confirma explícitamente en vez de asumir autorización previa.
- Prefiere editar archivos existentes a crear nuevos; no crees documentación (`*.md`) que no se
  pidió explícitamente.
