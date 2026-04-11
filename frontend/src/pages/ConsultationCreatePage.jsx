import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { ErrorMessage } from "../components/ErrorMessage";
import { LoadingBlock } from "../components/LoadingBlock";
import { SourceSummary } from "../components/SourceSummary";
import { consultationsService } from "../services/consultations";
import { legalService } from "../services/legal";

export function ConsultationCreatePage() {
  const navigate = useNavigate();
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [sources, setSources] = useState([]);
  const [documents, setDocuments] = useState([]);
  const [knowledgeLoading, setKnowledgeLoading] = useState(true);

  useEffect(() => {
    const loadKnowledge = async () => {
      try {
        const [sourcePayload, documentPayload] = await Promise.all([
          legalService.listSources(),
          legalService.listDocuments(),
        ]);
        setSources(sourcePayload.results || sourcePayload);
        setDocuments(documentPayload.results || documentPayload);
      } catch (requestError) {
        setError("No fue posible cargar el catalogo juridico inicial.");
      } finally {
        setKnowledgeLoading(false);
      }
    };

    loadKnowledge();
  }, []);

  const onSubmit = async (event) => {
    event.preventDefault();
    if (!prompt.trim()) {
      setError("Escribe una consulta antes de enviarla.");
      return;
    }

    setLoading(true);
    setError("");
    try {
      const consultation = await consultationsService.create(prompt.trim());
      setPrompt("");
      navigate(`/consultations/${consultation.id}`);
    } catch (requestError) {
      setError("No fue posible procesar la consulta. Revisa que el backend este disponible.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-grid">
      <section className="stack">
        <header className="page-header">
          <p className="eyebrow">Nueva consulta</p>
          <h2>Consulta juridica laboral en lenguaje natural</h2>
          <p className="muted">
            El backend guarda la consulta, detecta la materia, recupera evidencia y genera una
            respuesta estructurada con citas visibles.
          </p>
        </header>

        <form className="card stack" onSubmit={onSubmit}>
          <label className="field">
            <span>Describe el caso</span>
            <textarea
              rows="10"
              value={prompt}
              onChange={(event) => setPrompt(event.target.value)}
              placeholder="Ejemplo: tuve un accidente de trabajo y me quieren hacer firmar una renuncia."
            />
          </label>
          <button disabled={loading} type="submit">
            {loading ? "Procesando..." : "Enviar consulta"}
          </button>
        </form>
        <ErrorMessage message={error} />
      </section>

      <aside>
        {knowledgeLoading ? (
          <LoadingBlock label="Cargando fuentes y documentos..." />
        ) : (
          <SourceSummary sources={sources} documents={documents} />
        )}
      </aside>
    </div>
  );
}
