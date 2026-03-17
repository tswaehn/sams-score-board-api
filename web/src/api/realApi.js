const apiBaseUrl = "http://localhost:8000/api";
const fetchTimeoutMs = 60000;

function deepCopy(value) {
  return JSON.parse(JSON.stringify(value));
}

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

function createShortName(name) {
  const parts = name
    .split(/\s+/)
    .map((part) => part.replace(/[^A-Za-z0-9]/g, ""))
    .filter(Boolean);

  return parts.slice(0, 3).map((part) => part[0]).join("").toUpperCase();
}

function normalizeTeam(team) {
  return {
    uuid: team.uuid,
    name: team.name,
    short_name: createShortName(team.name),
    logo_url: team.logoImageLink
  };
}

function getSortedMatchGroups(data) {
  return Object.values(data["match-groups"] ?? {}).sort(
    (left, right) => left.tourneyLevel - right.tourneyLevel
  );
}

function getCompetitionUuidFromPath() {
  const match = window.location.pathname.match(/^\/competition\/([^/]+)(?:\/|$)/);
  return match?.[1] ?? "";
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

async function fetchCompetitionByUuid(uuid) {
  const response = await fetchWithTimeout(`${apiBaseUrl}/competition/${uuid}`);

  if (!response.ok) {
    throw new Error(
      `Failed to load ${apiBaseUrl}/competition/${uuid}: ${response.status}`
    );
  }

  return unwrapResponseData(await response.json());
}

async function fetchCompetitionList() {
  const response = await fetchWithTimeout(`${apiBaseUrl}/competition-list`);

  if (!response.ok) {
    throw new Error(
      `Failed to load ${apiBaseUrl}/competition-list: ${response.status}`
    );
  }

  return unwrapResponseData(await response.json());
}

async function fetchCurrentCompetitionData() {
  const uuid = getCompetitionUuidFromPath();

  if (!uuid) {
    throw new Error("Missing competition uuid");
  }

  const payload = await fetchCompetitionByUuid(uuid);
  return payload;
}

const handlers = {
  "/api/teams": async () => {
    const data = await fetchCurrentCompetitionData();

    return {
      competition: data.competition,
      association: data.association,
      season: data.season,
      teams: (data.teams ?? []).map(normalizeTeam)
    };
  },
  "/api/plan": async () => {
    const data = await fetchCurrentCompetitionData();

    return {
      competition: data.competition,
      association: data.association,
      season: data.season,
      teams: (data.teams ?? []).map(normalizeTeam),
      matchGroups: getSortedMatchGroups(data),
      rankings: data.rankings ?? {}
    };
  },
  "/api/live": async () => {
    const data = await fetchCurrentCompetitionData();

    return {
      competition: data.competition,
      association: data.association,
      season: data.season,
      matchGroups: getSortedMatchGroups(data)
    };
  },
  "/api/competition-list": fetchCompetitionList
};

export async function fetchJson(endpoint) {
  if (endpoint.startsWith("/api/competition/")) {
    const uuid = endpoint.slice("/api/competition/".length);

    if (!uuid) {
      throw new Error("Missing competition uuid");
    }

    return deepCopy(await fetchCompetitionByUuid(uuid));
  }

  const handler = handlers[endpoint];

  if (!handler) {
    throw new Error(`Unsupported real API endpoint: ${endpoint}`);
  }

  return deepCopy(await handler());
}
