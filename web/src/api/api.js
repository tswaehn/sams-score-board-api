import { useMediaQuery } from "@mui/material";
import { useTheme } from "@mui/material/styles";

const defaultApiBaseUrl = "http://localhost:8000/api";

export function getApiBaseUrl() {
  return window.__APP_CONFIG__?.apiBaseUrl ?? defaultApiBaseUrl;
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
