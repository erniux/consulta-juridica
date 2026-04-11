import { useEffect, useState } from "react";

import { ConsultationCard } from "../components/ConsultationCard";
import { ErrorMessage } from "../components/ErrorMessage";
import { LoadingBlock } from "../components/LoadingBlock";
import { consultationsService } from "../services/consultations";

function groupConsultations(consultations) {
  const groups = new Map();

  consultations.forEach((consultation) => {
    const groupKey = consultation.group_key || consultation.prompt.trim().toLowerCase();
    if (!groups.has(groupKey)) {
      groups.set(groupKey, {
        key: groupKey,
        attempts: [],
      });
    }

    groups.get(groupKey).attempts.push(consultation);
  });

  return Array.from(groups.values())
    .map((group) => ({
      ...group,
      attempts: [...group.attempts].sort(
        (left, right) => new Date(right.created_at) - new Date(left.created_at),
      ),
    }))
    .sort(
      (left, right) =>
        new Date(right.attempts[0]?.created_at || 0) -
        new Date(left.attempts[0]?.created_at || 0),
    );
}

export function ConsultationHistoryPage() {
  const [consultations, setConsultations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    const loadConsultations = async () => {
      try {
        const payload = await consultationsService.list();
        setConsultations(payload.results || payload);
      } catch (requestError) {
        setError("No fue posible cargar el historial.");
      } finally {
        setLoading(false);
      }
    };

    loadConsultations();
  }, []);

  const handleDelete = async (consultation) => {
    const confirmed = window.confirm(
      "Esta accion borrara el registro seleccionado de forma permanente. Deseas continuar?",
    );
    if (!confirmed) {
      return;
    }

    setDeletingId(consultation.id);
    setError("");
    try {
      await consultationsService.remove(consultation.id);
      setConsultations((currentConsultations) =>
        currentConsultations.filter((item) => item.id !== consultation.id),
      );
    } catch (requestError) {
      setError("No fue posible borrar la consulta seleccionada.");
    } finally {
      setDeletingId(null);
    }
  };

  const groupedConsultations = groupConsultations(consultations);

  return (
    <section className="stack">
      <header className="page-header">
        <p className="eyebrow">Historial</p>
        <h2>Consultas guardadas</h2>
        <p className="muted">
          Las consultas repetidas se agrupan para mostrar cuando se volvieron a realizar.
        </p>
      </header>

      <ErrorMessage message={error} />
      {loading ? (
        <LoadingBlock label="Cargando historial..." />
      ) : (
        <div className="stack">
          {groupedConsultations.length ? (
            groupedConsultations.map((group) => (
              <ConsultationCard
                key={group.key}
                deletingId={deletingId}
                group={group}
                onDelete={handleDelete}
              />
            ))
          ) : (
            <div className="card subtle">Aun no hay consultas registradas.</div>
          )}
        </div>
      )}
    </section>
  );
}
