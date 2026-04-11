import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { ErrorMessage } from "../components/ErrorMessage";
import { useAuth } from "../hooks/useAuth";

export function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [form, setForm] = useState({ username: "", password: "" });
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const redirectTo = location.state?.from?.pathname || "/consultations/new";

  useEffect(() => {
    setForm({ username: "", password: "" });
    setError("");
  }, [location.key]);

  const onSubmit = async (event) => {
    event.preventDefault();
    setLoading(true);
    setError("");

    try {
      await login(form.username, form.password);
      navigate(redirectTo, { replace: true });
    } catch (requestError) {
      setError("No fue posible iniciar sesion. Verifica usuario y contrasena.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-shell">
      <section className="auth-panel">
        <p className="eyebrow">Investigacion juridica asistida</p>
        <h1>Acceso al MVP</h1>
        <p className="muted">
          Usa la cuenta demo para probar el flujo inicial con JWT, historial y citas.
        </p>
        <form className="stack" onSubmit={onSubmit}>
          <label className="field">
            <span>Usuario</span>
            <input
              autoComplete="username"
              value={form.username}
              onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
              placeholder="Escribe tu usuario"
              type="text"
            />
          </label>
          <label className="field">
            <span>Contrasena</span>
            <input
              autoComplete="current-password"
              value={form.password}
              onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
              placeholder="Escribe tu contrasena"
              type="password"
            />
          </label>
          <button disabled={loading} type="submit">
            {loading ? "Entrando..." : "Iniciar sesion"}
          </button>
        </form>
        <ErrorMessage message={error} />
      </section>
    </div>
  );
}
