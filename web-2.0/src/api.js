const apiUrl = (window.SAMS_SCORE_BOARD_CONFIG?.apiUrl || "").replace(/\/$/, "");

export const apiPath = (path) => `${apiUrl}${path}`;

export async function getApiData(path, label) {
  const response = await fetch(apiPath(path));
  if (!response.ok) throw new Error(`The ${label} could not be loaded.`);
  const payload = await response.json();
  return Array.isArray(payload) ? payload : payload.data ?? [];
}
