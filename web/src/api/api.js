const defaultApiBaseUrl = "http://localhost:8000/api";

export function getApiBaseUrl() {
  return window.__APP_CONFIG__?.apiBaseUrl ?? defaultApiBaseUrl;
}

export { fetchJson } from "./realApi.js";
export {
  fetchLiveJson,
  fetchUpcomingMatchUuids,
  fetchMatchByUuid,
  fetchMatchesByCompetitionUuid
} from "./liveApi.js";
