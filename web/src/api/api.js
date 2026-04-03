const defaultApiBaseUrl = "http://localhost:8000/api";

export function getApiBaseUrl() {
  return window.__APP_CONFIG__?.apiBaseUrl ?? defaultApiBaseUrl;
}

export function getTeamShortName(name, shortName) {
  const normalizedShortName = shortName?.trim();

  if (normalizedShortName) {
    return normalizedShortName;
  }

  const normalizedName = name?.trim() ?? "";
  const words = normalizedName.split(/\s+/).filter(Boolean);
  const lastWordSuffix =
    words.length > 1 ? words[words.length - 1].slice(-3) : "";

  return `${normalizedName.slice(0, 5)}...${lastWordSuffix}`;
}

export { fetchJson } from "./realApi.js";
export {
  fetchLiveJson,
  fetchUpcomingMatchUuids,
  fetchMatchesByCompetitionUuid
} from "./liveApi.js";
