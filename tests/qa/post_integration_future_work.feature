# language: es
Feature: Finalización del trabajo futuro posterior a la integración

  @AC-FW-001
  Scenario: Consultar auditoría desde una única interfaz
    Given que existen eventos de seguridad y cambios de layout
    When un administrador accede al módulo de auditoría
    Then debe consultar ambos tipos de eventos
    And cada evento debe mostrar su dominio correspondiente
    And no debe perderse el contexto específico del evento

  @AC-FW-002
  Scenario: Registrar un cambio de layout en la auditoría unificada
    Given que un usuario modifica la posición de un gráfico
    When guarda el dashboard
    Then debe registrarse un evento con dominio DASHBOARD_LAYOUT
    And debe incluir la configuración anterior
    And debe incluir la configuración nueva

  @AC-FW-003
  Scenario: Registrar un inicio de sesión fallido
    Given que un usuario ingresa credenciales incorrectas
    When intenta iniciar sesión
    Then debe registrarse un evento LOGIN_FAILED
    And el evento debe pertenecer al dominio AUTHENTICATION
    And no debe registrar la contraseña ingresada

  @AC-FW-004
  Scenario: Aplicar el color institucional a botones Bootstrap
    Given que el color primario institucional está configurado
    When se renderiza un botón principal
    Then debe utilizar la variable de color primario de Bootstrap
    And no debe utilizar un color hardcodeado diferente

  @AC-FW-005
  Scenario: Aplicar el color institucional a enlaces
    Given que existe un color institucional para enlaces
    When se renderiza un enlace público
    Then debe utilizar el color configurado
    And debe mostrar un estado hover accesible

  @AC-FW-006
  Scenario: Visualizar la landing pública
    Given que un visitante no ha iniciado sesión
    When accede a la ruta principal
    Then debe visualizar la landing profesional
    And debe comprender el propósito de CMS Dashboards
    And debe visualizar las áreas de dashboards
    And debe poder navegar al login

  @AC-FW-007
  Scenario: Navegar por las secciones de la landing
    Given que un visitante se encuentra en la landing
    When selecciona una opción del menú
    Then debe desplazarse a la sección correspondiente
    And la sección no debe quedar oculta detrás del menú

  @AC-FW-008
  Scenario: Solicitar recuperación de contraseña
    Given que un usuario se encuentra en el login
    When selecciona "¿Olvidaste tu contraseña?"
    Then debe navegar a la pantalla de recuperación
    And debe poder ingresar su correo electrónico

  @AC-FW-009
  Scenario: No revelar si un usuario existe
    Given que se solicita recuperar una contraseña
    When el correo está o no registrado
    Then el sistema debe mostrar el mismo mensaje genérico
    And no debe revelar la existencia del usuario

  @AC-FW-010
  Scenario: Enviar un enlace válido de recuperación
    Given que el usuario está activo
    When solicita recuperar su contraseña
    Then debe generarse un token de un solo uso
    And debe enviarse un correo con un enlace de recuperación
    And debe registrarse el evento en auditoría

  @AC-FW-011
  Scenario: Rechazar un token expirado
    Given que el token de recuperación ha expirado
    When el usuario intenta cambiar su contraseña
    Then el sistema debe rechazar la solicitud
    And debe permitir solicitar un nuevo enlace

  @AC-FW-012
  Scenario: Utilizar una sola vez el token
    Given que un usuario cambió su contraseña correctamente
    When intenta reutilizar el mismo token
    Then el sistema debe rechazarlo

  @AC-FW-013
  Scenario: Cambiar la contraseña correctamente
    Given que el usuario tiene un token válido
    When ingresa y confirma una contraseña segura
    Then la contraseña debe almacenarse mediante hash
    And el token debe invalidarse
    And debe registrarse PASSWORD_RESET_COMPLETED
    And el usuario debe poder iniciar sesión con la nueva contraseña

  @AC-FW-014
  Scenario: Enviar correo QA al usuario indicado
    Given que el entorno de pruebas manuales tiene SMTP configurado
    And existe el usuario dpenarreta@grupolaar.com
    When se ejecuta el comando de prueba de recuperación
    Then debe enviarse un único correo de recuperación
    And el token no debe mostrarse completo en la consola
    And el envío debe quedar registrado en auditoría

  @AC-FW-015
  Scenario: No enviar correos reales durante pruebas unitarias
    Given que se ejecutan las pruebas automatizadas
    When se prueba la recuperación de contraseña
    Then debe utilizarse un backend de correo simulado
    And no debe enviarse un correo real

  @AC-FW-016
  Scenario: Mantener el diseño responsivo
    Given que un visitante utiliza una pantalla de 375 píxeles
    When visualiza la landing o recuperación de contraseña
    Then no debe existir desplazamiento horizontal
    And todos los controles deben ser utilizables
