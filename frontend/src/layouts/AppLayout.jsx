import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../hooks/useAuth";

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const userInitial = user?.username?.charAt(0)?.toUpperCase() || "U";

  const handleLogout = () => {
    logout();
    navigate("/login", { replace: true });
  };

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <nav className="nav-list nav-list-top" aria-label="Navegacion principal">
          <NavLink to="/consultations/new">Nueva consulta</NavLink>
          <NavLink to="/consultations">Historial</NavLink>
        </nav>

        <div className="sidebar-brand card compact">
          <p className="eyebrow">MVP RAG laboral</p>
          <h1>Consulta Juridica Laboral MX</h1>
          <p className="muted">
            Asistente de investigacion juridica con trazabilidad documental.
          </p>
        </div>
      </aside>

      <div className="content-shell">
        <header className="app-header">
          <div>
            <p className="eyebrow">Panel de trabajo</p>
            <h2>Investigacion juridica asistida</h2>
          </div>

          <div className="app-header-user">
            <div className="user-chip">
              <div className="user-avatar" aria-hidden="true">
                {userInitial}
              </div>
              <div className="user-summary">
                <p className="muted user-label">Sesion activa</p>
                <strong className="user-name">{user?.username}</strong>
                <span className="badge badge-light">{user?.role}</span>
              </div>
            </div>
            <button className="ghost-button header-logout" onClick={handleLogout} type="button">
              Cerrar sesion
            </button>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
