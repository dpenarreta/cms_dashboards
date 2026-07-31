# language: es
Feature: Integración de skelleton_base dentro de cms_dashboards

  @AC-INT-001
  Scenario: Mantener cms_dashboards como repositorio principal
    Given que cms_dashboards es el repositorio actual
    And skelleton_base es el repositorio fuente
    When se completa la integración
    Then todo el código final debe permanecer dentro de cms_dashboards
    And no debe reemplazarse el historial Git del repositorio principal

  @AC-INT-002
  Scenario: Generar el informe de diferencias
    Given que ambos repositorios están disponibles
    When se ejecuta la fase de análisis
    Then debe generarse una comparación de arquitectura
    And debe indicarse qué archivos se reutilizan
    And debe indicarse qué archivos se adaptan
    And debe indicarse qué archivos no se migran

  @AC-INT-003
  Scenario: Conservar la landing pública
    Given que cms_dashboards contiene una landing pública
    When se integra skelleton_base
    Then la landing debe continuar accesible
    And sus secciones deben continuar funcionando

  @AC-INT-004
  Scenario: Integrar el inicio de sesión
    Given que skelleton_base contiene autenticación
    When se completa la integración
    Then la ruta de login debe autenticar usuarios válidos
    And debe generar tokens seguros
    And las contraseñas no deben almacenarse en texto plano

  @AC-INT-005
  Scenario: Proteger un dashboard
    Given que un dashboard requiere un permiso
    And el usuario no tiene dicho permiso
    When intenta abrir el dashboard
    Then el backend debe rechazar el acceso
    And el frontend debe mostrar un mensaje de acceso restringido

  @AC-INT-006
  Scenario: Autorizar un dashboard
    Given que el usuario tiene el permiso requerido
    When accede al dashboard
    Then debe visualizar el dashboard
    And debe consultar únicamente las fuentes de datos autorizadas

  @AC-INT-007
  Scenario: Visualizar todos los dashboards como administrador general
    Given que el usuario tiene todos los permisos administrativos
    When accede al portal autenticado
    Then debe visualizar todos los dashboards
    And debe acceder a las configuraciones generales

  @AC-INT-008
  Scenario: Generar el menú según permisos
    Given que un usuario ha iniciado sesión
    When se obtiene su menú
    Then deben mostrarse únicamente los módulos autorizados
    And no deben mostrarse opciones sin permiso

  @AC-INT-009
  Scenario: Conservar el dashboard de cartera
    Given que el dashboard de cartera funcionaba antes de la integración
    When se completa la fusión
    Then sus KPI deben continuar funcionando
    And sus gráficos deben continuar funcionando
    And sus filtros deben continuar funcionando
    And sus matrices deben continuar funcionando

  @AC-INT-010
  Scenario: Evitar duplicidad de usuarios
    Given que ambos proyectos contienen modelos relacionados con usuarios
    When se consolida la arquitectura
    Then debe existir un único modelo principal de usuario
    And los roles y permisos deben relacionarse con ese modelo

  @AC-INT-011
  Scenario: Rechazar una llamada sin autenticación
    Given que un endpoint requiere autenticación
    When una solicitud no incluye un token válido
    Then debe responder con estado 401
    And no debe retornar información del dashboard

  @AC-INT-012
  Scenario: Rechazar una llamada sin permiso
    Given que un usuario está autenticado
    But no tiene el permiso requerido
    When consulta un endpoint restringido
    Then debe responder con estado 403

  @AC-INT-013
  Scenario: Registrar cambios administrativos
    Given que un administrador modifica los permisos de un rol
    When guarda los cambios
    Then la modificación debe registrarse en la auditoría

  @AC-INT-014
  Scenario: Mantener una única configuración institucional
    Given que ambos proyectos contienen configuración visual
    When se completa la integración
    Then debe existir una única fuente de configuración institucional
    And la landing, el login y el panel deben utilizarla

  @AC-INT-015
  Scenario: Ejecutar pruebas después de cada fase
    Given que se completa una fase de integración
    When se ejecutan las pruebas correspondientes
    Then no debe avanzarse dejando errores críticos sin corregir
