export function CitationList({ citations }) {
  if (!citations?.length) {
    return <p className="muted">No hay citas registradas para esta consulta.</p>;
  }

  return (
    <div className="stack">
      {citations.map((citation) => (
        <article key={citation.id} className="card">
          <h4>{citation.citation_label}</h4>
          <p className="muted">
            {citation.document_title} | {citation.source_name}
          </p>
          {citation.digital_registry_number ? (
            <p className="muted">
              Registro digital:{" "}
              {citation.official_url ? (
                <a
                  className="text-link inline-link"
                  href={citation.official_url}
                  rel="noreferrer"
                  target="_blank"
                >
                  {citation.digital_registry_number}
                </a>
              ) : (
                citation.digital_registry_number
              )}
            </p>
          ) : null}
          <p>{citation.snippet_used}</p>
        </article>
      ))}
    </div>
  );
}
