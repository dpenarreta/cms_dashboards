import { Navigate, Route, Routes } from 'react-router-dom'
import AdminLayout from '../components/admin/AdminLayout'
import RequirePermission from '../components/auth/RequirePermission'
import LandingPage from '../pages/public/LandingPage'
import LoginPage from '../pages/authentication/LoginPage'
import ForgotPasswordPage from '../pages/authentication/ForgotPasswordPage'
import ResetPasswordPage from '../pages/authentication/ResetPasswordPage'
import ForbiddenPage from '../pages/errors/ForbiddenPage'
import NotFoundPage from '../pages/errors/NotFoundPage'
import DashboardsListPage from '../pages/dashboards/DashboardsListPage'
import DashboardAreaPage from '../pages/dashboards/DashboardAreaPage'
import DashboardHistoricoPage from '../pages/dashboards/DashboardHistoricoPage'
import ProfilePage from '../pages/administration/profile/ProfilePage'
import UsersListPage from '../pages/administration/users/UsersListPage'
import UserFormPage from '../pages/administration/users/UserFormPage'
import RolesListPage from '../pages/administration/roles/RolesListPage'
import RoleFormPage from '../pages/administration/roles/RoleFormPage'
import PermissionsPage from '../pages/administration/permissions/PermissionsPage'
import SettingsPage from '../pages/administration/settings/SettingsPage'
import PlantillaBasePage from '../pages/administration/settings/PlantillaBasePage'
import EmailTemplatesPage from '../pages/administration/settings/EmailTemplatesPage'
import AuditListPage from '../pages/administration/audit/AuditListPage'

export default function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<LandingPage />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />
      <Route path="/reset-password" element={<ResetPasswordPage />} />
      <Route path="/403" element={<ForbiddenPage />} />

      {/* Toda la app autenticada (dashboards y administración) comparte un único layout de
          pantalla completa: la barra lateral debe verse siempre, en cualquier interfaz, no solo
          dentro de /admin. */}
      <Route element={<AdminLayout />}>
        <Route path="/app/dashboards" element={<RequirePermission><DashboardsListPage /></RequirePermission>} />
        {/* Sin `permission="dashboard.view"`: el control de acceso por dashboard (roles
            editores/lectores + dueño) puede darle acceso a un usuario puntual sin el permiso
            global — el backend es la única fuente de verdad (`GET .../layout` responde 403 si
            corresponde, y `DashboardAreaPage` lo muestra como error en vez de la grilla). */}
        <Route
          path="/app/dashboards/:dashboardId"
          element={(
            <RequirePermission>
              <DashboardAreaPage />
            </RequirePermission>
          )}
        />
        <Route
          path="/app/dashboards/:dashboardId/historico"
          element={(
            <RequirePermission>
              <DashboardHistoricoPage />
            </RequirePermission>
          )}
        />

        <Route path="/admin">
          <Route index element={<Navigate to="/admin/users" replace />} />
          {/* Sin `permission`: es la información propia del usuario autenticado, no un permiso
              administrativo — solo exige sesión, igual que las rutas de `/app/dashboards`. */}
          <Route path="profile" element={<RequirePermission><ProfilePage /></RequirePermission>} />
          <Route path="users" element={<RequirePermission permission="usuarios.ver"><UsersListPage /></RequirePermission>} />
          <Route path="users/new" element={<RequirePermission permission="usuarios.crear"><UserFormPage /></RequirePermission>} />
          <Route path="users/:id" element={<RequirePermission permission="usuarios.editar"><UserFormPage /></RequirePermission>} />
          <Route path="roles" element={<RequirePermission permission="roles.ver"><RolesListPage /></RequirePermission>} />
          <Route path="roles/new" element={<RequirePermission permission="roles.editar"><RoleFormPage /></RequirePermission>} />
          <Route path="roles/:id" element={<RequirePermission permission="roles.editar"><RoleFormPage /></RequirePermission>} />
          <Route path="permissions" element={<RequirePermission permission="permisos.ver"><PermissionsPage /></RequirePermission>} />
          <Route path="settings" element={<RequirePermission permission="configuracion.ver"><SettingsPage /></RequirePermission>} />
          <Route path="settings/plantilla-base" element={<RequirePermission permission="configuracion.ver"><PlantillaBasePage /></RequirePermission>} />
          <Route path="settings/email-templates" element={<RequirePermission permission="configuracion.ver"><EmailTemplatesPage /></RequirePermission>} />
          <Route path="audit" element={<RequirePermission permission="auditoria.ver"><AuditListPage /></RequirePermission>} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}
