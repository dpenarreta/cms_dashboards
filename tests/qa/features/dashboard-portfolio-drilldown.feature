# language: es
Feature: Visualización de cartera vencida por ciudad

  Como usuario autorizado del dashboard
  Quiero visualizar la cartera vencida distribuida por ciudad
  Para identificar la participación de cada ciudad y consultar su detalle

  @AC-CAR-001
  Scenario: Mostrar la cartera vencida por ciudad en un gráfico de pastel
    Given que existen registros de cartera vencida asociados con diferentes ciudades
    When el usuario abre el dashboard de cartera
    Then el sistema debe mostrar un gráfico de pastel de cartera vencida por ciudad
    And cada segmento debe representar una ciudad
    And el tamaño de cada segmento debe corresponder al monto vencido de la ciudad
    And no debe mostrarse la gráfica de Pareto anterior

  @AC-CAR-002
  Scenario: Mostrar la leyenda de ciudades consideradas
    Given que el gráfico de cartera vencida contiene información de varias ciudades
    When el gráfico es mostrado
    Then debe visualizarse una leyenda con todas las ciudades consideradas
    And cada ciudad debe asociarse visualmente con su segmento
    And la identificación no debe depender únicamente del color

  @AC-CAR-003
  Scenario: Mostrar monto y porcentaje de una ciudad
    Given que el gráfico de cartera vencida por ciudad está visible
    When el usuario posiciona el cursor sobre un segmento
    Then el sistema debe mostrar el nombre de la ciudad
    And debe mostrar el monto de cartera vencida
    And debe mostrar el porcentaje sobre el total
    And debe indicar que el segmento puede seleccionarse

  @AC-CAR-004
  Scenario: Abrir el detalle de cartera vencida de una ciudad
    Given que el usuario tiene permiso para consultar cartera
    And el gráfico de cartera vencida por ciudad está visible
    When el usuario selecciona el segmento correspondiente a Quito
    Then el sistema debe abrir la vista de detalle
    And debe aplicar el filtro de estado de cartera vencida
    And debe aplicar el filtro de la ciudad seleccionada
    And debe conservar los filtros globales del dashboard
    And solo debe mostrar registros que cumplan todos los filtros

  @AC-CAR-005
  Scenario: Consultar registros gestionados desde el estado general de cartera
    Given que el indicador de estado general de cartera está visible
    When el usuario selecciona la categoría Gestionado
    Then el sistema debe abrir la vista de detalle
    And debe aplicar el filtro de estado de gestión Gestionado
    And debe mostrar únicamente registros gestionados
    And debe conservar los filtros generales activos

  @AC-CAR-006
  Scenario: Seleccionar una columna de otro gráfico
    Given que existe un gráfico con categorías consultables
    When el usuario selecciona una columna
    Then el sistema debe identificar el gráfico de origen
    And debe identificar la categoría seleccionada
    And debe transformar la selección en filtros válidos
    And debe abrir la vista de detalle con esos filtros aplicados

  @AC-CAR-007
  Scenario: Conservar el contexto al regresar al dashboard
    Given que el usuario abrió un detalle desde un gráfico
    And existían filtros globales activos
    When el usuario regresa al dashboard
    Then los filtros globales deben conservarse
    And el dashboard debe mantener el contexto de navegación
    And el usuario no debe configurar nuevamente los filtros

  @AC-CAR-008
  Scenario: Coincidencia entre el valor del gráfico y el detalle
    Given que un segmento del gráfico muestra un monto de cartera vencida
    When el usuario abre el detalle de ese segmento
    Then la suma de los registros filtrados debe coincidir con el monto del gráfico
    And ambos resultados deben usar los mismos filtros
    And ambos resultados deben aplicar las mismas reglas de cálculo

  @AC-CAR-009
  Scenario: Rechazar el acceso de un usuario sin permisos
    Given que un usuario autenticado no tiene permiso para consultar el detalle de cartera
    When selecciona un elemento interactivo del dashboard
    Then el backend debe rechazar la solicitud
    And no debe retornar información de cartera
    And el frontend debe mostrar un mensaje de acceso denegado

  @AC-CAR-010
  Scenario: Mostrar una vista sin resultados
    Given que el usuario seleccionó una categoría del gráfico
    And no existen registros que cumplan los filtros actuales
    When se abre la vista de detalle
    Then el sistema debe mostrar un estado sin resultados
    And debe mostrar los filtros aplicados
    And debe permitir regresar al dashboard

  @AC-CAR-011
  Scenario: Paginar el detalle desde el backend
    Given que el detalle contiene más registros que el tamaño máximo de página
    When el usuario abre el detalle
    Then el backend debe retornar los resultados paginados
    And el frontend debe mostrar controles de paginación
    And no debe descargar toda la cartera en una sola respuesta

  @AC-CAR-012
  Scenario: Abrir la agrupación de otras ciudades
    Given que las ciudades con participación menor fueron agrupadas como Otras ciudades
    When el usuario selecciona el segmento Otras ciudades
    Then el sistema debe mostrar las ciudades incluidas en la agrupación
    And debe consultar los registros de todas esas ciudades
    And no debe incluir registros de ciudades externas a la agrupación

  @AC-CAR-013
  Scenario: Navegar mediante teclado
    Given que el gráfico contiene elementos interactivos
    When el usuario navega mediante teclado
    Then debe poder enfocar los elementos seleccionables
    And debe poder abrir el detalle usando el teclado
    And debe existir una indicación visual de foco

  @AC-CAR-014
  Scenario: Seleccionar el saldo pendiente por recuperador
    Given que el gráfico de saldo pendiente por recuperador está visible
    When el usuario selecciona la barra de un recuperador
    Then el sistema debe abrir la vista de detalle
    And debe aplicar el filtro de ese recuperador
    And no debe restringir por estado de cartera

  @AC-CAR-015
  Scenario: Seleccionar un segmento de causales por recuperador
    Given que el gráfico de causales por recuperador está visible
    When el usuario selecciona el segmento de una causal dentro de la barra de un recuperador
    Then el sistema debe abrir la vista de detalle
    And debe aplicar el filtro del recuperador seleccionado
    And debe aplicar el filtro de la causal seleccionada

  @AC-CAR-016
  Scenario: Seleccionar una celda de la matriz de recuperadores y causales
    Given que la matriz de recuperadores y causales está visible
    When el usuario selecciona una celda de la matriz
    Then el sistema debe abrir la vista de detalle
    And debe aplicar el filtro del recuperador de la fila
    And debe aplicar el filtro de la causal de la columna

  @AC-CAR-017
  Scenario: Seleccionar una tarjeta KPI de mora mayor a 120 días
    Given que la tarjeta KPI "Cartera > 120 días" está visible
    When el usuario selecciona esa tarjeta
    Then el sistema debe abrir la vista de detalle
    And debe aplicar el filtro de estado de cartera vencida
    And debe aplicar el filtro de días vencidos mayor a 120

  @AC-CAR-018
  Scenario: Quitar un filtro generado por el drill-down sin perder los filtros globales
    Given que el usuario abrió el detalle de una ciudad con un filtro global de recuperador activo
    When el usuario quita el filtro de ciudad desde la vista de detalle
    Then el filtro de ciudad debe eliminarse
    And el filtro global de recuperador debe seguir aplicado
    And el filtro de estado de cartera vencida debe seguir aplicado
