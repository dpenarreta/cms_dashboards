# language: es
Feature: Dashboard de cartera desde archivo Excel

  Scenario: Cargar un archivo Excel válido
    Given que el usuario se encuentra en la página del dashboard de cartera
    When carga un archivo Excel con todas las columnas obligatorias
    Then el sistema debe validar correctamente el archivo
    And debe mostrar la cantidad de filas encontradas
    And debe habilitar el botón para procesar el dashboard

  Scenario: Rechazar un archivo sin la columna de saldo
    Given que el usuario carga un archivo Excel
    And el archivo no contiene una columna asociada a Saldo
    When intenta validar el archivo
    Then el sistema debe indicar que falta la columna Saldo
    And no debe procesar el dashboard

  Scenario: Calcular la fecha de corte del mes anterior
    Given que la fecha actual del servidor es 29 de julio de 2026
    When el sistema procesa el archivo
    Then la fecha de corte predeterminada debe ser 30 de junio de 2026

  Scenario: Calcular la cartera vencida
    Given un documento con saldo mayor a cero
    And su fecha de vencimiento es anterior o igual a la fecha de corte
    When se procesa el archivo
    Then el saldo debe contabilizarse como cartera vencida

  Scenario: Calcular la cartera no vencida
    Given un documento con saldo mayor a cero
    And su fecha de vencimiento es posterior a la fecha de corte
    When se procesa el archivo
    Then el saldo debe contabilizarse como cartera no vencida

  Scenario: Identificar cartera mayor a 120 días
    Given un documento vencido hace más de 120 días
    When se procesa el archivo
    Then su saldo debe incluirse en el indicador de cartera mayor a 120 días

  Scenario: Identificar cartera mayor a 360 días
    Given un documento vencido hace más de 360 días
    When se procesa el archivo
    Then su saldo debe incluirse en el indicador de cartera mayor a 360 días

  Scenario: Contar clientes únicos por RUC
    Given que un cliente tiene varios documentos con el mismo RUC
    When se procesa el archivo
    Then el cliente debe contarse una sola vez

  Scenario: Mostrar los diez clientes con mayor saldo
    Given que el archivo contiene más de diez clientes
    When se genera el gráfico de principales deudores
    Then deben mostrarse los diez clientes con mayor suma de saldo
    And deben ordenarse de mayor a menor

  Scenario: Mostrar las causales vacías como sin gestión
    Given que un documento no tiene valor en la columna Causal
    When se procesa el archivo
    Then el documento debe clasificarse como SIN GESTIÓN
    And debe aparecer en los gráficos de causal

  Scenario: Utilizar Vendedor 3 como recuperador
    Given que el archivo contiene las columnas Vendedor 3 y Vendedor / Ejecutivo Ventas
    When se procesa el dashboard
    Then el responsable de recuperación debe obtenerse de Vendedor 3
    And no debe obtenerse de Vendedor / Ejecutivo Ventas

  Scenario: Generar el Pareto de cartera vencida por ciudad
    Given que existen documentos vencidos en varias ciudades
    When se genera el Pareto
    Then las ciudades deben ordenarse por saldo vencido descendente
    And debe calcularse el porcentaje acumulado
    And debe mostrarse una referencia del 80 por ciento

  Scenario: Mostrar las causales por recuperador
    Given que cada recuperador tiene documentos con diferentes causales
    When se genera el gráfico de recuperadores y causales
    Then debe mostrarse el saldo agrupado por recuperador y causal
    And las causales vacías deben mostrarse como SIN GESTIÓN

  Scenario: Recalcular al cambiar la fecha de corte
    Given que el dashboard ya fue procesado
    When el usuario modifica la fecha de corte
    Then todos los indicadores deben recalcularse
    And todos los gráficos deben actualizarse
