import { useMediaQuery } from "@mui/material";
import { useTheme } from "@mui/material/styles";

const defaultApiBaseUrl = "http://localhost:8000/api";
const clientSessionStorageKey = "sams-scoreboard-client-id";
let inMemoryClientSessionId = null;

export function getApiBaseUrl() {
  return window.__APP_CONFIG__?.apiBaseUrl ?? defaultApiBaseUrl;
}

function createClientSessionId() {
  const timestamp = Date.now().toString(36);
  const randomPart = Math.random().toString(36).slice(2, 12);

  return `client-${timestamp}-${randomPart}`;
}

export function getClientSessionId() {
    let storedClientId = null;

  try {
    storedClientId = window.localStorage.getItem(clientSessionStorageKey);
  } catch (error) {
    storedClientId = null;
  }

  if (storedClientId) {
    inMemoryClientSessionId = storedClientId;
    return storedClientId;
  }

  if (inMemoryClientSessionId) {
    return inMemoryClientSessionId;
  }

  const nextClientId = createClientSessionId();
  inMemoryClientSessionId = nextClientId;

  try {
    window.localStorage.setItem(clientSessionStorageKey, nextClientId);
  } catch (error) {
    return nextClientId;
  }

  return nextClientId;
}

export function withClientSessionId(url) {
  const trackedUrl = new URL(url, window.location.origin);
  trackedUrl.searchParams.set("client_id", getClientSessionId());
  return trackedUrl.toString();
}

export function getTeamShortName(name, shortName, maxLength = 25) {
  const normalizedShortName = shortName?.trim();
  const normalizedName = name?.trim() ?? "";
  const sourceName = normalizedShortName || normalizedName;

  if (sourceName.length <= maxLength) {
    return sourceName;
  }

  if (maxLength <= 2) {
    return ".".repeat(Math.max(maxLength, 0));
  }

  const availableChars = maxLength - 2;
  const leftLength = Math.ceil(availableChars / 2);
  const rightLength = Math.floor(availableChars / 2);
  const rightPart = rightLength > 0 ? sourceName.slice(-rightLength) : "";

  return `${sourceName.slice(0, leftLength)}..${rightPart}`;
}

export function useIsMobile() {
  const theme = useTheme();

  return useMediaQuery(theme.breakpoints.down("md"));
}

export { fetchJson } from "./realApi.js";
export {
  fetchLiveJson,
  fetchUpcomingMatchUuids,
  fetchMatchesBySeriesUuid
} from "./liveApi.js";
