import examplePayload from "./example.json";

const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
const competitionListUrl = "/competition-list.json";

function deepCopy(value) {
  return JSON.parse(JSON.stringify(value));
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

function getExampleData() {
  return examplePayload.data;
}

function getSortedMatchGroups(data) {
  return Object.values(data["match-groups"]).sort(
    (left, right) => left.tourneyLevel - right.tourneyLevel
  );
}

async function getCompetitionList() {
  const response = await fetch(competitionListUrl);

  if (!response.ok) {
    throw new Error(`Failed to load ${competitionListUrl}: ${response.status}`);
  }

  return response.json();
}

const handlers = {
  "/api/teams": () => {
    const data = getExampleData();

    return {
      competition: data.competition,
      association: data.association,
      season: data.season,
      teams: data.teams.map(normalizeTeam)
    };
  },
  "/api/plan": () => {
    const data = getExampleData();

    return {
      competition: data.competition,
      association: data.association,
      season: data.season,
      teams: data.teams.map(normalizeTeam),
      matchGroups: getSortedMatchGroups(data),
      rankings: data.rankings
    };
  },
  "/api/live": () => {
    const data = getExampleData();

    return {
      competition: data.competition,
      association: data.association,
      season: data.season,
      matchGroups: getSortedMatchGroups(data)
    };
  },
  "/api/competition-list": getCompetitionList
};

export async function fetchJson(endpoint) {
  await delay(450);

  const handler = handlers[endpoint];

  if (!handler) {
    throw new Error(`Unknown endpoint: ${endpoint}`);
  }

  return deepCopy(await handler());
}
