const API = "/api";

export async function apiRequest(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    credentials: "same-origin",
    ...options,
  });
  const payload =
    response.status === 204
      ? null
      : response.headers.get("content-type")?.includes("application/json")
        ? await response.json()
        : null;
  if (!response.ok) {
    const error = new Error(
      payload?.detail || `Request failed (${response.status})`,
    );
    error.status = response.status;
    throw error;
  }
  return payload;
}
