import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import {
  Button,
  Box,
  FormControl,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography
} from "@mui/material";
import { fetchJson } from "../api/api.js";
import { layout } from "../components/layout.js";
import {
  getEntityConfig,
  getEntityFromPath,
  setSelectedEntity
} from "../entities/entity.js";

const filterSteps = [
  {
    key: "association",
    label: "Association",
    getValue: (entry) => entry.association?.shortname ?? ""
  },
  {
    key: "season",
    label: "Season",
    getValue: (entry) => entry.season?.name ?? ""
  },
  {
    key: "name",
    label: "Name",
    getValue: (entry) => entry.name ?? ""
  },
  {
    key: "gender",
    label: "Gender",
    getValue: (entry) => entry.gender ?? ""
  },
  {
    key: "shortname",
    label: "Short Name",
    getValue: (entry) => entry.shortname ?? ""
  }
];

function sortOptions(options) {
  return [...options].sort((left, right) =>
    left.localeCompare(right, undefined, { numeric: true, sensitivity: "base" })
  );
}

function formatGender(value) {
  if (!value) {
    return "Unknown";
  }

  return `${value.slice(0, 1)}${value.slice(1).toLowerCase()}`;
}

function getStepOptions(entries, step) {
  const values = new Set();

  entries.forEach((entry) => {
    const value = step.getValue(entry);

    if (value) {
      values.add(value);
    }
  });

  return sortOptions([...values]);
}

function getFilteredEntries(entries, selections, maxStepIndex) {
  return entries.filter((entry) =>
    filterSteps.slice(0, maxStepIndex + 1).every((step) => {
      const selectedValue = selections[step.key];

      if (!selectedValue) {
        return true;
      }

      return step.getValue(entry) === selectedValue;
    })
  );
}

const selectSx = {
  bgcolor: "teamInfo.main",
  "& .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(20, 17, 15, 0.08)"
  },
  "&:hover .MuiOutlinedInput-notchedOutline": {
    borderColor: "rgba(20, 17, 15, 0.16)"
  }
};

function getDefaultSelectedFilters() {
  return {
    association: "",
    season: "",
    gender: "",
    name: "",
    shortname: "",
    uuid: ""
  };
}

function readStoredSelectedFilters(storageKey) {
  try {
    const rawValue = window.localStorage.getItem(storageKey);

    if (!rawValue) {
      return getDefaultSelectedFilters();
    }

    return {
      ...getDefaultSelectedFilters(),
      ...JSON.parse(rawValue)
    };
  } catch {
    return getDefaultSelectedFilters();
  }
}

export default function EntitySelection({ entityType }) {
  const entityConfig = getEntityConfig(entityType);
  const storageKey = `${entityType}-list-filters`;
  const navigate = useNavigate();
  const location = useLocation();
  const [entries, setEntries] = useState([]);
  const [selectedFilters, setSelectedFilters] = useState(() => readStoredSelectedFilters(storageKey));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const appliedEntity = getEntityFromPath(location.pathname);

  useEffect(() => {
    let isMounted = true;

    fetchJson(`/api/${entityType}-list`)
      .then((data) => {
        if (isMounted) {
          setEntries(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [entityType]);

  useEffect(() => {
    window.localStorage.setItem(storageKey, JSON.stringify(selectedFilters));
  }, [selectedFilters, storageKey]);

  useEffect(() => {
    if (entries.length === 0) {
      return;
    }

    setSelectedFilters((current) => {
      const nextSelections = { ...getDefaultSelectedFilters(), ...current };

      filterSteps.forEach((step, index) => {
        const availableEntries = getFilteredEntries(entries, nextSelections, index - 1);
        const options = getStepOptions(availableEntries, step);

        if (nextSelections[step.key] && !options.includes(nextSelections[step.key])) {
          nextSelections[step.key] = "";

          filterSteps.slice(index + 1).forEach((followingStep) => {
            nextSelections[followingStep.key] = "";
          });

          nextSelections.uuid = "";
        }
      });

      const fullyFiltered = getFilteredEntries(entries, nextSelections, filterSteps.length - 1);
      const availableUuids = new Set(fullyFiltered.map((entry) => entry.uuid));

      if (nextSelections.uuid && !availableUuids.has(nextSelections.uuid)) {
        nextSelections.uuid = "";
      }

      return JSON.stringify(current) !== JSON.stringify(nextSelections)
        ? nextSelections
        : current;
    });
  }, [entries]);

  const selections = filterSteps.map((step, index) => {
    const filteredEntries = getFilteredEntries(entries, selectedFilters, index - 1);

    return {
      ...step,
      filteredEntries,
      options: getStepOptions(filteredEntries, step),
      selectedValue: selectedFilters[step.key],
      visible: index === 0 || Boolean(selectedFilters[filterSteps[index - 1].key])
    };
  });

  const fullyFilteredEntries = getFilteredEntries(entries, selectedFilters, filterSteps.length - 1);
  const uuidOptions = sortOptions([
    ...new Set(fullyFilteredEntries.map((entry) => entry.uuid))
  ]);
  const showUuidCards =
    Boolean(selectedFilters.shortname) &&
    fullyFilteredEntries.length > 1 &&
    fullyFilteredEntries.length < 5;
  const resolvedEntry =
    fullyFilteredEntries.find((entry) => entry.uuid === selectedFilters.uuid) ??
    (fullyFilteredEntries.length === 1 ? fullyFilteredEntries[0] : null);

  const handleFilterChange = (key, value) => {
    const stepIndex = filterSteps.findIndex((step) => step.key === key);
    const nextSelections = { ...selectedFilters, [key]: value };

    filterSteps.slice(stepIndex + 1).forEach((step) => {
      nextSelections[step.key] = "";
    });

    nextSelections.uuid = "";
    setSelectedFilters(nextSelections);
  };

  return (
    <Box sx={{ display: "grid", gap: layout.gap.page }}>
      {loading && (
        <Typography color="text.secondary">
          Loading {entityConfig.singularLabel.toLowerCase()} list...
        </Typography>
      )}
      {error && (
        <Typography color="error" sx={{ fontWeight: 600 }}>
          {error}
        </Typography>
      )}

      {!loading && !error && (
        <Paper
          elevation={0}
          sx={{
            p: layout.padding.surface,
            borderRadius: layout.radius.surface,
            border: "1px solid rgba(20, 17, 15, 0.08)",
            bgcolor: "background.paper",
            gap: layout.gap.section
          }}
        >
          <Stack spacing={layout.gap.section}>
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {entityConfig.singularLabel} List
              </Typography>
              <Typography color="text.secondary">
                Filters are ordered by how strongly they reduce the dataset:
                association, season, name, gender, then short name.
              </Typography>
            </Box>

            <Stack spacing={layout.gap.section}>
              {selections
                .filter((selection) => selection.visible)
                .map((selection) => (
                  <FormControl key={selection.key} fullWidth>
                    <InputLabel id={`${selection.key}-label`}>
                      {selection.label}
                    </InputLabel>
                    <Select
                      labelId={`${selection.key}-label`}
                      value={selection.selectedValue}
                      label={selection.label}
                      sx={selectSx}
                      onChange={(event) =>
                        handleFilterChange(selection.key, event.target.value)
                      }
                    >
                      <MenuItem value="">
                        <em>Select {selection.label}</em>
                      </MenuItem>
                      {selection.options.map((option) => (
                        <MenuItem key={option} value={option}>
                          {selection.key === "gender" ? formatGender(option) : option}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                ))}

              {Boolean(selectedFilters.shortname) && uuidOptions.length > 1 && !showUuidCards && (
                <FormControl fullWidth>
                  <InputLabel id="uuid-label">UUID</InputLabel>
                  <Select
                    labelId="uuid-label"
                    value={selectedFilters.uuid}
                    label="UUID"
                    sx={selectSx}
                    onChange={(event) =>
                      setSelectedFilters((current) => ({
                        ...current,
                        uuid: event.target.value
                      }))
                    }
                  >
                    <MenuItem value="">
                      <em>Select UUID</em>
                    </MenuItem>
                    {uuidOptions.map((option) => (
                      <MenuItem key={option} value={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
            </Stack>

            <Typography color="text.secondary" variant="body2">
              Matching entries: {fullyFilteredEntries.length}
            </Typography>

            {showUuidCards && (
              <Stack spacing={layout.gap.cardList}>
                {fullyFilteredEntries.map((entry) => (
                  <Paper
                    key={entry.uuid}
                    elevation={0}
                    sx={{
                      p: layout.padding.card,
                      borderRadius: layout.radius.surface,
                      border: "1px solid rgba(20, 17, 15, 0.08)",
                      bgcolor: "teamInfo.main"
                    }}
                  >
                    <Stack spacing={0.5}>
                      <Typography
                        variant="subtitle2"
                        color="text.secondary"
                        sx={{ wordBreak: "break-all" }}
                      >
                        {entry.uuid}
                      </Typography>
                      <Typography sx={{ fontWeight: 600 }}>
                        {entry.name}
                      </Typography>
                      <Typography color="text.secondary">
                        {entry.shortname}
                      </Typography>
                      <Box sx={{ pt: 1 }}>
                        <Button
                          variant="contained"
                          onClick={() =>
                            setSelectedFilters((current) => ({
                              ...current,
                              uuid: entry.uuid
                            }))
                          }
                        >
                          Select
                        </Button>
                      </Box>
                    </Stack>
                  </Paper>
                ))}
              </Stack>
            )}

            {resolvedEntry && (
              <Paper
                elevation={0}
                sx={{
                  p: layout.padding.card,
                  borderRadius: layout.radius.surface,
                  border: "1px solid rgba(20, 17, 15, 0.08)",
                  bgcolor: "teamInfo.main"
                }}
              >
                <Stack spacing={0.5}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Selected UUID
                  </Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, wordBreak: "break-all" }}>
                    {resolvedEntry.uuid}
                  </Typography>
                  <Typography color="text.secondary">
                    {resolvedEntry.association?.name} · {resolvedEntry.season?.name} ·{" "}
                    {formatGender(resolvedEntry.gender)}
                  </Typography>
                  <Typography sx={{ fontWeight: 600 }}>
                    {resolvedEntry.name}
                  </Typography>
                  <Typography color="text.secondary">
                    {resolvedEntry.shortname}
                  </Typography>
                  <Box sx={{ pt: 1, display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Button
                      variant="contained"
                      onClick={() => {
                        setSelectedEntity(entityType, resolvedEntry.uuid);
                        navigate(`${entityConfig.routeBase}/${resolvedEntry.uuid}/teams`);
                      }}
                    >
                      Apply
                    </Button>
                    {appliedEntity.entityType === entityType &&
                      appliedEntity.entityUuid === resolvedEntry.uuid && (
                      <Typography color="text.secondary" variant="body2">
                        Saved as the selected {entityConfig.singularLabel.toLowerCase()}
                      </Typography>
                    )}
                  </Box>
                </Stack>
              </Paper>
            )}
          </Stack>
        </Paper>
      )}
    </Box>
  );
}

