import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";

import { CitationList } from "../components/CitationList";
import { ErrorMessage } from "../components/ErrorMessage";
import { LoadingBlock } from "../components/LoadingBlock";
import { StatusBadge } from "../components/StatusBadge";
import { consultationsService } from "../services/consultations";
import { formatDate, parseAnswerSections } from "../utils/format";

export function ConsultationDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [consultation, setConsultation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [deleting, setDeleting] = useState(false);
  const [loadError, setLoadError] = useState("");
  const [actionError, setActionError] = useState("");

  useEffect(() => {
    const loadConsultation = async () => {
      try {
        const payload = await consultationsService.detail(id);
        setConsultation(payload);
      } catch (requestError) {
        setLoadError("No fue posible cargar el detalle de la consulta.");
      } finally {
        setLoading(false);
      }
    };

    loadConsultation();
  }, [id]);

  if (loading) {
    return <LoadingBlock label="Cargando detalle..." />;
  }

  if (loadError) {
    return <ErrorMessage message={loadError} />;
  }

  const sections = parseAnswerSections(consultation.final_answer);

  const handleDelete = async () => {
    const confirmed = window.confirm(
      "Esta accion borrara la consulta actual de forma permanente. Deseas continuar?",
    );
    if (!confirmed) {
      return;
    }

    setDeleting(true);
    setActionError("");
    try {
      await consultationsService.remove(consultation.id);
      navigate("/consultations", { replace: true });
    } catch (requestError) {
      setActionError("No fue posible borrar esta consulta.");
      setDeleting(false);
    }
  };

  return (
    <div className="page-grid detail-grid">
      <section className="stack">
        <ErrorMessage message={actionError} />
        <header className="page-header">
          <div className="header-row">
            <div>
              <p className="eyebrow">Detalle de consulta</p>
              <h2>Consulta #{consultation.id}</h2>
            </div>
            <StatusBadge status={consultation.status} />
          </div>
          <p className="muted">Creada el {formatDate(consultation.created_at)}</p>
          <p>{consultation.prompt}</p>
        </header>

        <section className="stack">
          {sections.map((section) => (
            <article key={section.headline} className="card">
              <h3>{section.headline}</h3>
              <pre className="answer-block">{section.body}</pre>
            </article>
          ))}
        </section>

        <section className="card">
          <h3>Fragmentos recuperados</h3>
          <div className="stack compact">
            {consultation.retrievals.map((retrieval) => (
              <div key={retrieval.id} className="retrieval-row">
                <div>
                  <strong>{retrieval.fragment.document_title}</strong>
                  <p className="muted">
                    {retrieval.fragment.title} | score {retrieval.score}
                  </p>
                  {retrieval.fragment.digital_registry_number ? (
                    <p className="muted">
                      Registro digital:{" "}
                      {retrieval.fragment.official_url ? (
                        <a
                          className="text-link inline-link"
                          href={retrieval.fragment.official_url}
                          rel="noreferrer"
                          target="_blank"
                        >
                          {retrieval.fragment.digital_registry_number}
                        </a>
                      ) : (
                        retrieval.fragment.digital_registry_number
                      )}
                    </p>
                  ) : null}
                  {retrieval.fragment.official_url ? (
                    <a
                      className="text-link retrieval-link"
                      href={retrieval.fragment.official_url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      Leer fuente oficial
                    </a>
                  ) : null}
                </div>
                <span className="badge badge-light">{retrieval.retrieval_type}</span>
              </div>
            ))}
          </div>
        </section>
      </section>

      <aside className="stack">
        <section className="card">
          <h3>Citas visibles</h3>
          <CitationList citations={consultation.citations} />
        </section>

        <section className="card">
          <h3>Metadatos</h3>
          <p className="muted">Modelo: {consultation.model_name || "pendiente"}</p>
          <p className="muted">
            Materia: {consultation.detected_matter || "sin clasificar"}
          </p>
          <p className="muted">
            Temas: {(consultation.detected_topics_json || []).join(", ") || "sin temas"}
          </p>
        </section>

        <Link className="ghost-button full-width" to="/consultations">
          Volver al historial
        </Link>
        <button
          className="ghost-button full-width danger-button"
          disabled={deleting}
          onClick={handleDelete}
          type="button"
        >
          {deleting ? "Borrando..." : "Borrar consulta"}
        </button>
      </aside>
    </div>
  );
}
