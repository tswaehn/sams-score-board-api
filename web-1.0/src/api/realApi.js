import { getApiBaseUrl, getTeamShortName, withClientSessionId } from "./api.js";
import { getEntityFromPath } from "../entities/entity.js";

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

function normalizeTeam(team) {
  return {
    uuid: team.uuid,
    name: team.name,
    short_name: getTeamShortName(
      team.name,
      team.shortName ?? team.short_name ?? team.shortname
    ),
    logo_url: team.logoImageLink
  };
}

function getSortedMatchGroups(data) {
  return Object.values(data["match-groups"] ?? {}).sort(
    (left, right) => left.tourneyLevel - right.tourneyLevel
  );
}

function getSortedMatchDays(data) {
  return Object.values(data["match-days"] ?? {}).sort((left, right) =>
    `${left.matchdate ?? ""}`.localeCompare(`${right.matchdate ?? ""}`)
  );
}

async function fetchWithTimeout(url) {
  const controller = new AbortController();
  const timeoutId = window.setTimeout(() => controller.abort(), fetchTimeoutMs);

  try {
    return await fetch(withClientSessionId(url), { signal: controller.signal });
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

async function fetchEntityByTypeAndUuid(entityType, uuid) {
  const apiBaseUrl = getApiBaseUrl();
  const response = await fetchWithTimeout(`${apiBaseUrl}/${entityType}/${uuid}`);

  if (!response.ok) {
    throw new Error(
      `Failed to load ${apiBaseUrl}/${entityType}/${uuid}: ${response.status}`
    );
  }

  return unwrapResponseData(await response.json());
}

async function fetchEntityList(entityType) {
  const apiBaseUrl = getApiBaseUrl();
  const response = await fetchWithTimeout(`${apiBaseUrl}/${entityType}-list`);

  if (!response.ok) {
    throw new Error(
      `Failed to load ${apiBaseUrl}/${entityType}-list: ${response.status}`
    );
  }

  return unwrapResponseData(await response.json());
}

async function fetchCurrentEntityData() {
  const { entityType, entityUuid } = getEntityFromPath(window.location.pathname);

  if (!entityType || !entityUuid) {
    throw new Error("Missing entity route context");
  }

  return fetchEntityByTypeAndUuid(entityType, entityUuid);
}

const handlers = {
  "/api/teams": async () => {
    const data = await fetchCurrentEntityData();
    const entity = data.competition ?? data.league ?? null;

    return {
      entityType: data.entityType ?? (data.competition ? "competition" : "league"),
      entity,
      competition: data.competition,
      league: data.league,
      association: data.association,
      season: data.season,
      teams: (data.teams ?? []).map(normalizeTeam)
    };
  },
  "/api/plan": async () => {
    const data = await fetchCurrentEntityData();
    const entity = data.competition ?? data.league ?? null;

    return {
      entityType: data.entityType ?? (data.competition ? "competition" : "league"),
      entity,
      competition: data.competition,
      league: data.league,
      association: data.association,
      season: data.season,
      teams: (data.teams ?? []).map(normalizeTeam),
      matchGroups: getSortedMatchGroups(data),
      matchDays: getSortedMatchDays(data),
      rankings: data.rankings ?? {}
    };
  },
  "/api/competition-list": () => fetchEntityList("competition"),
  "/api/league-list": () => fetchEntityList("league")
};

export async function fetchJson(endpoint) {
  if (endpoint.startsWith("/api/competition/")) {
    const uuid = endpoint.slice("/api/competition/".length);

    if (!uuid) {
      throw new Error("Missing competition uuid");
    }

    return deepCopy(await fetchEntityByTypeAndUuid("competition", uuid));
  }

  if (endpoint.startsWith("/api/league/")) {
    const uuid = endpoint.slice("/api/league/".length);

    if (!uuid) {
      throw new Error("Missing league uuid");
    }

    return deepCopy(await fetchEntityByTypeAndUuid("league", uuid));
  }

  const handler = handlers[endpoint];

  if (!handler) {
    throw new Error(`Unsupported real API endpoint: ${endpoint}`);
  }

  return deepCopy(await handler());
}
