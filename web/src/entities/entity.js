export const selectedEntityTypeStorageKey = "selected-entity-type";
export const selectedEntityUuidStorageKey = "selected-entity-uuid";

export function getEntityConfig(entityType) {
  if (entityType === "league") {
    return {
      type: "league",
      singularLabel: "League",
      pluralLabel: "Leagues",
      listPath: "/leagues",
      routeBase: "/league"
    };
  }

  return {
    type: "competition",
    singularLabel: "Competition",
    pluralLabel: "Competitions",
    listPath: "/competitions",
    routeBase: "/competition"
  };
}

export function getEntityFromPath(pathname) {
  const match = pathname.match(/^\/(competition|league)\/([^/]+)(?:\/|$)/);

  if (!match) {
    return { entityType: "", entityUuid: "" };
  }

  return {
    entityType: match[1],
    entityUuid: match[2]
  };
}

export function getSelectedEntity() {
  const entityType = window.localStorage.getItem(selectedEntityTypeStorageKey);
  const entityUuid = window.localStorage.getItem(selectedEntityUuidStorageKey);
  const legacyCompetitionUuid = window.localStorage.getItem("competition-uuid");

  if (entityType && entityUuid) {
    return { entityType, entityUuid };
  }

  if (legacyCompetitionUuid) {
    return { entityType: "competition", entityUuid: legacyCompetitionUuid };
  }

  return { entityType: "", entityUuid: "" };
}

export function setSelectedEntity(entityType, entityUuid) {
  window.localStorage.setItem(selectedEntityTypeStorageKey, entityType);
  window.localStorage.setItem(selectedEntityUuidStorageKey, entityUuid);

  if (entityType === "competition") {
    window.localStorage.setItem("competition-uuid", entityUuid);
  } else {
    window.localStorage.removeItem("competition-uuid");
  }
}

export function clearSelectedEntity() {
  window.localStorage.removeItem(selectedEntityTypeStorageKey);
  window.localStorage.removeItem(selectedEntityUuidStorageKey);
  window.localStorage.removeItem("competition-uuid");
}
