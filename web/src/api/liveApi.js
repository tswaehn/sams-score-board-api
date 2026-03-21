const fetchTimeoutMs = 60000;
const defaultApiBaseUrl = "http://localhost:8000/api";
const apiBaseUrl = window.__APP_CONFIG__?.apiBaseUrl ?? defaultApiBaseUrl;
const liveApiUrl = `${apiBaseUrl}/live`;

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

export async function fetchLiveJson(path = "") {
  const url = path ? `${liveApiUrl}${path}` : liveApiUrl;
  const response = await fetchWithTimeout(url);

  if (!response.ok) {
    throw new Error(`Failed to load ${url}: ${response.status}`);
  }

  return unwrapResponseData(await response.json());
}

export async function fetchUpcomingMatchUuids(competitionUuid) {
  if (!competitionUuid) {
    throw new Error("Missing competition uuid");
  }

  const payload = await fetchLiveJson();
  const now = Date.now();

  return payload.matchDays
    .flatMap((matchDay) => matchDay.matches ?? [])
    .filter(
      (match) => match.matchSeries === competitionUuid && Number(match.date) >= now
    )
    .sort((left, right) => left.date - right.date)
    .map((match) => match.id);
}

export async function fetchMatchByUuid(matchUuid) {
  if (!matchUuid) {
    throw new Error("Missing match uuid");
  }

  const payload = await fetchLiveJson();
  const match = payload.matchDays
    .flatMap((matchDay) => matchDay.matches ?? [])
    .find((entry) => entry.id === matchUuid);

  if (!match) {
    throw new Error(`Match not found: ${matchUuid}`);
  }

  return {
    ...match,
    matchState: payload.matchStates?.[matchUuid] ?? null,
    matchStats: payload.matchStats?.[matchUuid] ?? null,
    matchSeriesData: payload.matchSeries?.[match.matchSeries] ?? null
  };
}

export async function fetchMatchesByCompetitionUuid(competitionUuid) {
  if (!competitionUuid) {
    throw new Error("Missing competition uuid");
  }

  const payload = await fetchLiveJson();

  return payload.matchDays
    .flatMap((matchDay) => matchDay.matches ?? [])
    .filter((match) => match.matchSeries === competitionUuid)
    .sort((left, right) => left.date - right.date)
    .map((match) => ({
      ...match,
      matchState: payload.matchStates?.[match.id] ?? null,
      matchStats: payload.matchStats?.[match.id] ?? null,
      matchSeriesData: payload.matchSeries?.[match.matchSeries] ?? null
    }));
}
