export function ErrorMessage({ message }) {
  if (!message) {
    return null;
  }
  return <div className="card error">{message}</div>;
}
