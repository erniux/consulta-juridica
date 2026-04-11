export function formatDate(value) {
  if (!value) {
    return "Sin fecha";
  }
  return new Intl.DateTimeFormat("es-MX", {
    dateStyle: "medium",
    timeStyle: value.includes("T") ? "short" : undefined,
  }).format(new Date(value));
}

export function parseAnswerSections(answer) {
  if (!answer) {
    return [];
  }

  return answer
    .split(/\n(?=\d+\.\s)/)
    .map((section) => section.trim())
    .filter(Boolean)
    .map((section) => {
      const [headline, ...rest] = section.split("\n");
      return {
        headline,
        body: rest.join("\n").trim(),
      };
    });
}
