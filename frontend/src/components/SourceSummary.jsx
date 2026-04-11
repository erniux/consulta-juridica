export function SourceSummary({ sources, documents }) {
  return (
    <div className="stack">
      <section className="card">
        <h3>Fuentes activas</h3>
        <div className="stack compact">
          {sources.map((source) => (
            <div key={source.id}>
              <strong>{source.name}</strong>
              <p className="muted">{source.authority}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="card">
        <h3>Documentos indexados</h3>
        <div className="stack compact">
          {documents.map((document) => (
            <div key={document.id}>
              <strong>{document.short_name}</strong>
              <p className="muted">
                {document.document_type} | {document.fragment_count || 0} fragmentos
              </p>
              {document.digital_registry_number ? (
                <p className="muted">
                  Registro digital:{" "}
                  {document.official_url ? (
                    <a
                      className="text-link inline-link"
                      href={document.official_url}
                      rel="noreferrer"
                      target="_blank"
                    >
                      {document.digital_registry_number}
                    </a>
                  ) : (
                    document.digital_registry_number
                  )}
                </p>
              ) : null}
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
