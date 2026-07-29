# language: es
Feature: Personalización y edición visual del dashboard

  Como usuario autorizado del dashboard
  Quiero reordenar, redimensionar, ocultar y personalizar (título/descripción/color) los
  componentes del dashboard de cartera
  Para adaptar la presentación a mis necesidades sin perder la coherencia de los datos

  @AC-EDT-001
  Scenario: Activar el modo edición
    Given que el usuario tiene permiso para editar el dashboard
    When el usuario pulsa "Editar dashboard"
    Then el sistema debe mostrar el borde y los controles de edición en cada componente
    And debe mostrar los botones Vista previa, Restablecer diseño, Cancelar y Guardar cambios

  @AC-EDT-002
  Scenario: Un usuario sin permiso de edición no ve el botón de editar
    Given que el usuario no tiene el permiso "dashboard.edit"
    When el usuario abre el dashboard
    Then el sistema no debe mostrar el botón "Editar dashboard"
    And no debe ser posible entrar en modo edición

  @AC-EDT-003
  Scenario: Un usuario sin permiso de ver el dashboard no ve ningún control del editor
    Given que el usuario no tiene el permiso "dashboard.view"
    When el usuario abre el dashboard
    Then el sistema no debe renderizar ningún control de la barra de edición

  @AC-EDT-004
  Scenario: Reordenar un componente arrastrándolo
    Given que el modo edición está activo
    When el usuario arrastra un componente a una nueva posición
    Then el componente debe ocupar la nueva posición inmediatamente en el borrador
    And el resto de componentes debe conservar su orden relativo

  @AC-EDT-005
  Scenario: Reordenar un componente con los botones de mover (alternativa accesible)
    Given que el modo edición está activo
    When el usuario pulsa "Mover abajo" en un componente
    Then ese componente debe intercambiar su posición con el siguiente
    And el cambio debe reflejarse igual que si se hubiera arrastrado

  @AC-EDT-006
  Scenario: Mover un componente al inicio o al final
    Given que el modo edición está activo
    When el usuario pulsa "Mover al inicio" en un componente que no es el primero
    Then el componente debe pasar a ser el primero
    When el usuario pulsa "Mover al final" en ese mismo componente
    Then el componente debe pasar a ser el último

  @AC-EDT-007
  Scenario: Cambiar el ancho de un componente con el selector discreto
    Given que el panel de configuración de un componente está abierto
    When el usuario elige "6 columnas — 50%" en el selector de ancho
    Then el componente debe ocupar la mitad del ancho disponible
    And ningún otro componente debe superponerse con él

  @AC-EDT-008
  Scenario: Cambiar el alto de un componente con un preset
    Given que el panel de configuración de un componente está abierto
    When el usuario elige el preset de alto "Grande (600px)"
    Then el componente debe ajustar su altura a ese valor

  @AC-EDT-009
  Scenario: Editar el título de un componente
    Given que el panel de configuración de un componente está abierto
    When el usuario escribe un nuevo título
    Then el componente debe mostrar el nuevo título de inmediato en el borrador

  @AC-EDT-010
  Scenario: Editar el color principal de un componente con un valor válido
    Given que el panel de configuración de un componente está abierto
    When el usuario introduce el color hexadecimal "#1F4E78"
    Then el componente debe aplicar ese color sin mostrar ningún error

  @AC-EDT-011
  Scenario: Rechazar un color con formato inválido
    Given que el panel de configuración de un componente está abierto
    When el usuario introduce un valor que no es un color hexadecimal válido
    Then el sistema debe mostrar un mensaje de color inválido
    And no debe aplicar ese color al componente

  @AC-EDT-012
  Scenario: Sanitizar contenido potencialmente inseguro en el título
    Given que el usuario guarda un título que contiene una etiqueta "<script>"
    When el backend valida y guarda la configuración
    Then el backend debe eliminar la etiqueta del texto
    And debe conservar el resto del texto legítimo sin alterarlo

  @AC-EDT-013
  Scenario: No corromper texto legítimo que contiene el símbolo ">"
    Given que un componente tiene un título como "Cartera > 120 días"
    When el usuario guarda la configuración sin modificar ese título
    Then el backend debe conservar el título exactamente igual
    And no debe eliminar el símbolo ">" ni ningún carácter legítimo

  @AC-EDT-014
  Scenario: Ocultar un componente
    Given que el modo edición está activo
    When el usuario pulsa "Ocultar" en un componente
    Then el componente debe mostrarse como oculto en el editor
    And no debe mostrarse en la vista normal del dashboard tras guardar

  @AC-EDT-015
  Scenario: Mostrar nuevamente un componente oculto
    Given que un componente está oculto en el borrador
    When el usuario pulsa "Mostrar" sobre ese componente
    Then el componente debe volver a mostrarse con su contenido normal

  @AC-EDT-016
  Scenario: Guardar cambios persiste la configuración
    Given que el usuario realizó cambios de orden, tamaño, color y visibilidad
    When el usuario pulsa "Guardar cambios"
    Then el backend debe almacenar la nueva configuración con una versión incrementada
    And al recargar el dashboard debe mostrarse la configuración guardada

  @AC-EDT-017
  Scenario: Cancelar con cambios sin guardar pide confirmación
    Given que el usuario realizó cambios sin guardarlos
    When el usuario pulsa "Cancelar"
    Then el sistema debe pedir confirmación antes de descartar los cambios
    And solo debe revertir el borrador si el usuario confirma

  @AC-EDT-018
  Scenario: Cancelar sin cambios pendientes no pide confirmación
    Given que el usuario no realizó ningún cambio en el borrador
    When el usuario pulsa "Cancelar"
    Then el sistema debe salir del modo edición sin mostrar ningún diálogo

  @AC-EDT-019
  Scenario: Restablecer el diseño predeterminado pide confirmación
    Given que el modo edición está activo
    When el usuario pulsa "Restablecer diseño"
    Then el sistema debe advertir que la acción reemplaza la configuración para todos los usuarios
    And solo debe restablecer el diseño si el usuario confirma

  @AC-EDT-020
  Scenario: Conflicto de versión al guardar de forma concurrente
    Given que dos personas abrieron el editor con la misma versión del layout
    And la primera persona guardó sus cambios
    When la segunda persona intenta guardar con la versión desactualizada
    Then el backend debe rechazar el guardado con un conflicto de versión
    And el frontend debe ofrecer recargar la configuración más reciente sin perder el trabajo silenciosamente

  @AC-EDT-021
  Scenario: Auditoría de cambios
    Given que el usuario guardó una nueva configuración con su nombre para auditoría
    When se consulta el historial de cambios del dashboard
    Then debe existir un registro con quién hizo el cambio, cuándo y qué tipo de cambio fue

  @AC-EDT-022
  Scenario: La vista previa oculta el chrome de edición sin round-trip al backend
    Given que el modo edición está activo con cambios sin guardar
    When el usuario activa "Vista previa"
    Then el sistema debe ocultar los controles de edición y mostrar el dashboard como quedaría
    And no debe enviar ninguna solicitud al backend para mostrar la vista previa

  @AC-EDT-023
  Scenario: Cambiar un estilo no vuelve a consultar los datos del dashboard
    Given que el dashboard ya cargó sus datos (KPIs, gráficos, filtros)
    When el usuario cambia el color o el título de un componente en el editor
    Then el sistema no debe volver a solicitar los datos de cartera al backend
    And los valores mostrados deben seguir siendo los mismos que ya se habían cargado

  @AC-EDT-024
  Scenario: Reordenar los campos dentro del panel de filtros
    Given que el panel de configuración del panel de filtros está abierto
    When el usuario mueve un campo de filtro hacia arriba en la lista de campos
    Then ese campo debe aparecer antes que los demás dentro del panel de filtros
    And el resto de componentes del dashboard no debe verse afectado

  @AC-EDT-025
  Scenario: Los componentes nunca se superponen y no aparece scroll horizontal
    Given que el usuario cambió el ancho y el orden de varios componentes
    When el dashboard se renderiza en modo normal o en modo edición
    Then ningún componente debe superponerse visualmente con otro
    And la página no debe requerir desplazamiento horizontal

  @AC-EDT-026
  Scenario: El dashboard editable funciona en una pantalla angosta (móvil)
    Given que el usuario accede desde una pantalla angosta
    When el dashboard se muestra en modo normal o en modo edición
    Then cada componente debe adaptar su ancho a la pantalla disponible
    And los controles de edición deben seguir siendo utilizables sin desbordar la pantalla

  @AC-EDT-027
  Scenario: Rechazar un componente desconocido al guardar
    Given que la solicitud de guardado incluye un identificador de componente no reconocido
    When el backend valida la configuración
    Then debe rechazar la solicitud sin persistir ningún cambio
    And no debe crear un componente nuevo con ese identificador

  @AC-EDT-028
  Scenario: Un usuario sin permiso para restablecer no ve esa opción
    Given que el usuario no tiene el permiso "dashboard.configuration.reset"
    When el usuario activa el modo edición
    Then el sistema no debe mostrar el botón "Restablecer diseño"
    And el resto de las acciones de edición permitidas deben seguir disponibles
