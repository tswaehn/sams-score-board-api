import { getApiBaseUrl } from "./api.js";

const fetchTimeoutMs = 60000;

function unwrapResponseData(payload) {
  if (
    payload &&
    typeof payload === "object" &&
    !Array.isArray(payload) &&
    "data" in payload
  ) {
    return payload.data;
  }

  return payload;
}

async function fetchWithTimeout(url) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), fetchTimeoutMs);

  try {
    return await fetch(url, { signal: controller.signal });
  } catch (error) {
    if (error.name === "AbortError") {
      throw new Error(`Request timed out after ${fetchTimeoutMs}ms: ${url}`);
    }

    if (error instanceof TypeError) {
      throw new Error(`Network error while loading ${url}: ${error.message}`);
    }

    throw error;
  } finally {
    window.clearTimeout(timeoutId);
  }
}

export async function fetchLiveJson({ seriesUuid, path = "" } = {}) {
  const liveApiUrl = `${getApiBaseUrl()}/live`;
  const scopedLiveApiUrl = seriesUuid
    ? `${liveApiUrl}/${seriesUuid}`
    : liveApiUrl;
  const url = new URL(path ? `${scopedLiveApiUrl}${path}` : scopedLiveApiUrl, window.location.origin);

  const response = await fetchWithTimeout(url);

  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`);
  }

  return unwrapResponseData(await response.json());
}

export async function fetchUpcomingMatchUuids(seriesUuid) {
  if (!seriesUuid) {
    throw new Error("Missing live series uuid");
  }

  const payload = await fetchLiveJson({ seriesUuid });
  const now = Date.now();

  return payload.matchDays
    .flatMap((matchDay) => matchDay.matches ?? [])
    .filter((match) => Number(match.date) >= now)
    .sort((left, right) => left.date - right.date)
    .map((match) => match.id);
}

export async function fetchMatchesBySeriesUuid(seriesUuid) {
  if (!seriesUuid) {
    throw new Error("Missing live series uuid");
  }

  const payload = await fetchLiveJson({ seriesUuid });

  return payload.matchDays
    .flatMap((matchDay) => matchDay.matches ?? [])
    .sort((left, right) => left.date - right.date)
    .map((match) => ({
      ...match,
      matchState: payload.matchStates?.[match.id] ?? null,
      matchStats: payload.matchStats?.[match.id] ?? null,
      matchSeriesData: payload.matchSeries?.[match.matchSeries] ?? null
    }));
}
