# language: es
Feature: Configuración de registros visibles en matrices

  Como usuario del dashboard de cartera
  Quiero elegir cuántos registros se muestran por página en cada tabla o matriz
  Para consultar cómodamente conjuntos de datos grandes o pequeños sin perder mis filtros

  @AC-PAG-001
  Scenario: Mostrar diez registros de forma predeterminada
    Given que una matriz no tiene una configuración específica
    When se carga el dashboard
    Then la matriz debe mostrar diez registros por página
    And el selector debe mostrar el valor 10

  @AC-PAG-002
  Scenario: Seleccionar cinco registros por página
    Given que la matriz contiene más de cinco registros
    When el usuario selecciona mostrar 5 registros
    Then la matriz debe mostrar un máximo de cinco registros
    And debe regresar a la primera página

  @AC-PAG-003
  Scenario Outline: Seleccionar una cantidad permitida
    Given que la matriz contiene suficientes registros
    When el usuario selecciona mostrar <cantidad> registros
    Then la matriz debe mostrar como máximo <cantidad> registros por página

    Examples:
      | cantidad |
      | 5        |
      | 10       |
      | 25       |
      | 50       |
      | 100      |

  @AC-PAG-004
  Scenario: Mantener filtros al cambiar la cantidad de registros
    Given que el usuario ha aplicado un filtro por causal
    When cambia la cantidad de registros de 10 a 25
    Then el filtro por causal debe mantenerse
    And la matriz debe regresar a la primera página
    And debe mostrar hasta 25 registros filtrados

  @AC-PAG-005
  Scenario: Mantener el ordenamiento
    Given que la matriz está ordenada por saldo descendente
    When el usuario cambia la cantidad de registros visibles
    Then el ordenamiento por saldo debe mantenerse

  @AC-PAG-006
  Scenario: Configurar la cantidad predeterminada en modo edición
    Given que el usuario tiene permiso para editar el dashboard
    And ha activado el modo edición
    When configura 50 registros visibles por defecto
    And guarda los cambios
    Then la matriz debe utilizar 50 registros por página al volver a cargarla

  @AC-PAG-007
  Scenario: No modificar la configuración general desde la visualización
    Given que la matriz tiene 10 registros configurados por defecto
    When un usuario visualizador selecciona temporalmente 25 registros
    Then la matriz debe mostrar 25 registros durante la sesión
    But la configuración general debe continuar siendo 10

  @AC-PAG-008
  Scenario: Validar un tamaño de página no permitido
    Given que se envía una solicitud con page_size igual a 500
    When el backend procesa la solicitud
    Then debe utilizar el tamaño predeterminado
    And no debe retornar más de 100 registros

  @AC-PAG-009
  Scenario: Mostrar el resumen de resultados
    Given que existen 248 registros
    And la página actual es la segunda
    And se muestran 25 registros por página
    When se renderiza la matriz
    Then debe mostrarse el texto "Mostrando 26 a 50 de 248 registros"

  @AC-PAG-010
  Scenario: Exportar todos los resultados filtrados
    Given que la matriz muestra 25 registros por página
    And existen 248 resultados filtrados
    When el usuario selecciona exportar todos los resultados
    Then el archivo exportado debe contener los 248 registros
    And no únicamente los 25 registros visibles

  @AC-PAG-011
  Scenario: Adaptar la paginación en dispositivos móviles
    Given que el usuario visualiza la matriz en una pantalla de 375 píxeles
    When se renderizan los controles de paginación
    Then no debe existir desplazamiento horizontal
    And el selector debe seguir siendo utilizable
