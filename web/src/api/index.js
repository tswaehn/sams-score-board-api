import { fetchJson as fetchMockJson } from "./mockApi.js";
import { fetchJson as fetchRealJson } from "./realApi.js";

const testing = false;

export async function fetchJson(endpoint) {
  if (testing) {
    return fetchMockJson(endpoint);
  }

  return fetchRealJson(endpoint);
}
