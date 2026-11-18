export function errorText(error: any): string {
  if (!error) return "";
  const data = error?.response?.data || error;
  try {
    const messages = JSON.parse(data._server_messages || "[]")
      .map((m: string) => JSON.parse(m).message)
      .join(" ");
    if (messages) return new DOMParser().parseFromString(messages, "text/html").body.textContent || messages;
  } catch {
    /* Server errors without a message array use the fallback below. */
  }
  return (
    data.message ||
    data.exception?.split(":").slice(1).join(":") ||
    error.message ||
    "The request could not be completed."
  );
}
export async function rawPost(method: string, args: Record<string, unknown>) {
  const response = await fetch("/api/method/" + method, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", "X-Frappe-CSRF-Token": window.csrf_token || "" },
    body: JSON.stringify(args),
  });
  const data = await response.json();
  if (!response.ok) throw data;
  return data;
}
export async function upload(name: string, file: File, doctype = "IA Maturity Assessment") {
  const form = new FormData();
  form.append("name", name);
  form.append("doctype", doctype);
  form.append("file", file);
  const response = await fetch("/api/method/ia_maturity.grc.api.upload_evidence", {
    method: "POST",
    credentials: "same-origin",
    headers: { "X-Frappe-CSRF-Token": window.csrf_token || "" },
    body: form,
  });
  const data = await response.json();
  if (!response.ok) throw data;
  return data.message;
}
