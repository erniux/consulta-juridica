import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <div className="card">
      <h2>Ruta no encontrada</h2>
      <p className="muted">La pagina solicitada no existe en este MVP.</p>
      <Link className="text-link" to="/consultations/new">
        Ir a nueva consulta
      </Link>
    </div>
  );
}
