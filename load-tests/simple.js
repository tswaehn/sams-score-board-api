import http from "k6/http";
import { check, sleep } from "k6";

const baseUrl = __ENV.BASE_URL || "http://127.0.0.1:8000";
const apiBaseUrl = `${baseUrl.replace(/\/$/, "")}/api`;
const competitionId = __ENV.COMPETITION_ID;
const pauseSeconds = Number(__ENV.SLEEP_SECONDS || "1");

export const options = {
  thresholds: {
    http_req_failed: ["rate<0.05"],
    http_req_duration: ["p(95)<1000"],
  },
  scenarios: {
    api_smoke_load: {
      executor: "ramping-vus",
      startVUs: 1,
      stages: [
        { duration: "60s", target: 250 },
        { duration: "120s", target: 500 },
        { duration: "3m", target: 500 },
        { duration: "15s", target: 0 },
      ],
      gracefulRampDown: "10s",
    },
  },
};

function get(path) {
  return http.get(`${apiBaseUrl}${path}`, {
    headers: {
      Accept: "application/json",
    },
    tags: { endpoint: path },
  });
}

export default function () {
  const healthResponse = get("/healthz");
  check(healthResponse, {
    "healthz returns 200": (response) => response.status === 200,
  });

  const liveResponse = get("/live");
  check(liveResponse, {
    "live returns 200": (response) => response.status === 200,
  });

  const listResponse = get("/competition-list");
  check(listResponse, {
    "competition-list returns 200": (response) => response.status === 200,
  });

  if (competitionId) {
    const competitionResponse = get(`/competition/${competitionId}`);
    check(competitionResponse, {
      "competition returns 200": (response) => response.status === 200,
    });
  }

  sleep(pauseSeconds);
}
