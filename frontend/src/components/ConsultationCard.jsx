import { Link } from "react-router-dom";

import { formatDate } from "../utils/format";
import { StatusBadge } from "./StatusBadge";

export function ConsultationCard({ group, deletingId, onDelete }) {
  const latestConsultation = group.attempts[0];

  return (
    <article className="card consultation-card">
      <div className="consultation-card-header">
        <div className="consultation-card-status">
          <StatusBadge status={latestConsultation.status} />
          {group.attempts.length > 1 ? (
            <span className="badge badge-light">{group.attempts.length} registros</span>
          ) : null}
        </div>
        <span className="muted">{formatDate(latestConsultation.created_at)}</span>
      </div>
      <h3>{latestConsultation.prompt}</h3>
      <p className="muted">
        Materia detectada: {latestConsultation.detected_matter || "pendiente"} | Citas:{" "}
        {latestConsultation.citation_count ?? 0}
      </p>
      {group.attempts.length > 1 ? (
        <p className="muted">Esta misma consulta se volvio a realizar en las siguientes fechas:</p>
      ) : null}

      <div className="attempt-list">
        {group.attempts.map((consultation, index) => (
          <div key={consultation.id} className="attempt-row">
            <div className="attempt-info">
              <strong>{index === 0 ? "Ultima consulta" : `Reconsulta ${index}`}</strong>
              <p className="muted">{formatDate(consultation.created_at)}</p>
            </div>

            <div className="attempt-actions">
              <Link className="text-link" to={`/consultations/${consultation.id}`}>
                Ver detalle
              </Link>
              <button
                className="ghost-button attempt-delete"
                disabled={deletingId === consultation.id}
                onClick={() => onDelete(consultation)}
                type="button"
              >
                {deletingId === consultation.id ? "Borrando..." : "Borrar"}
              </button>
            </div>
          </div>
        ))}
      </div>
    </article>
  );
}
