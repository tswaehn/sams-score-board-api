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
import { fetchJson } from "../api/index.js";

const competitionListFiltersStorageKey = "competition-list-filters";
const selectedCompetitionUuidStorageKey = "competition-uuid";

const filterSteps = [
  {
    key: "association",
    label: "Association",
    getValue: (competition) => competition.association?.shortname ?? ""
  },
  {
    key: "season",
    label: "Season",
    getValue: (competition) => competition.season?.name ?? ""
  },
  {
    key: "name",
    label: "Competition Name",
    getValue: (competition) => competition.name ?? ""
  },
  {
    key: "gender",
    label: "Gender",
    getValue: (competition) => competition.gender ?? ""
  },
  {
    key: "shortname",
    label: "Short Name",
    getValue: (competition) => competition.shortname ?? ""
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

function getStepOptions(competitions, step) {
  const values = new Set();

  competitions.forEach((competition) => {
    const value = step.getValue(competition);

    if (value) {
      values.add(value);
    }
  });

  return sortOptions([...values]);
}

function getFilteredCompetitions(competitions, selections, maxStepIndex) {
  return competitions.filter((competition) =>
    filterSteps.slice(0, maxStepIndex + 1).every((step) => {
      const selectedValue = selections[step.key];

      if (!selectedValue) {
        return true;
      }

      return step.getValue(competition) === selectedValue;
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

function getCompetitionUuidFromPath(pathname) {
  const match = pathname.match(/^\/competition\/([^/]+)(?:\/|$)/);
  return match?.[1] ?? "";
}

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

function readStoredSelectedFilters() {
  try {
    const rawValue = window.localStorage.getItem(competitionListFiltersStorageKey);

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

export default function CompetitionList() {
  const navigate = useNavigate();
  const location = useLocation();
  const [competitions, setCompetitions] = useState([]);
  const [selectedFilters, setSelectedFilters] = useState(readStoredSelectedFilters);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const appliedUuid = getCompetitionUuidFromPath(location.pathname);

  useEffect(() => {
    let isMounted = true;

    fetchJson("/api/competition-list")
      .then((data) => {
        if (isMounted) {
          setCompetitions(data);
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
  }, []);

  useEffect(() => {
    window.localStorage.setItem(
      competitionListFiltersStorageKey,
      JSON.stringify(selectedFilters)
    );
  }, [selectedFilters]);

  useEffect(() => {
    if (competitions.length === 0) {
      return;
    }

    setSelectedFilters((current) => {
      const nextSelections = { ...getDefaultSelectedFilters(), ...current };

      filterSteps.forEach((step, index) => {
        const availableCompetitions = getFilteredCompetitions(
          competitions,
          nextSelections,
          index - 1
        );
        const options = getStepOptions(availableCompetitions, step);

        if (
          nextSelections[step.key] &&
          !options.includes(nextSelections[step.key])
        ) {
          nextSelections[step.key] = "";

          filterSteps.slice(index + 1).forEach((followingStep) => {
            nextSelections[followingStep.key] = "";
          });

          nextSelections.uuid = "";
        }
      });

      const fullyFiltered = getFilteredCompetitions(
        competitions,
        nextSelections,
        filterSteps.length - 1
      );
      const availableUuids = new Set(fullyFiltered.map((competition) => competition.uuid));

      if (nextSelections.uuid && !availableUuids.has(nextSelections.uuid)) {
        nextSelections.uuid = "";
      }

      const changed =
        JSON.stringify(current) !== JSON.stringify(nextSelections);

      return changed ? nextSelections : current;
    });
  }, [competitions]);

  const selections = filterSteps.map((step, index) => {
    const filteredCompetitions = getFilteredCompetitions(
      competitions,
      selectedFilters,
      index - 1
    );

    return {
      ...step,
      filteredCompetitions,
      options: getStepOptions(filteredCompetitions, step),
      selectedValue: selectedFilters[step.key],
      visible: index === 0 || Boolean(selectedFilters[filterSteps[index - 1].key])
    };
  });

  const fullyFilteredCompetitions = getFilteredCompetitions(
    competitions,
    selectedFilters,
    filterSteps.length - 1
  );
  const uuidOptions = sortOptions([
    ...new Set(fullyFilteredCompetitions.map((competition) => competition.uuid))
  ]);
  const showUuidCards =
    Boolean(selectedFilters.shortname) &&
    fullyFilteredCompetitions.length > 1 &&
    fullyFilteredCompetitions.length < 5;
  const resolvedCompetition =
    fullyFilteredCompetitions.find(
      (competition) => competition.uuid === selectedFilters.uuid
    ) ?? (fullyFilteredCompetitions.length === 1 ? fullyFilteredCompetitions[0] : null);

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
    <Box sx={{ display: "grid", gap: 2 }}>
      {loading && (
        <Typography color="text.secondary">
          Loading competition list...
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
            p: 2,
            borderRadius: 3,
            border: "1px solid rgba(20, 17, 15, 0.08)",
            bgcolor: "background.paper",
            gap: 2
          }}
        >
          <Stack spacing={2}>
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                Competition List
              </Typography>
              <Typography color="text.secondary">
                Filters are ordered by how strongly they reduce the dataset:
                association, season, competition name, gender, then short name.
              </Typography>
            </Box>

            <Stack spacing={2}>
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

              {Boolean(selectedFilters.shortname) &&
                uuidOptions.length > 1 &&
                !showUuidCards && (
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
              Matching entries: {fullyFilteredCompetitions.length}
            </Typography>

            {showUuidCards && (
              <Stack spacing={1.2}>
                {fullyFilteredCompetitions.map((competition) => (
                  <Paper
                    key={competition.uuid}
                    elevation={0}
                    sx={{
                      p: 1.5,
                      borderRadius: 2.5,
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
                        {competition.uuid}
                      </Typography>
                      <Typography sx={{ fontWeight: 600 }}>
                        {competition.name}
                      </Typography>
                      <Typography color="text.secondary">
                        {competition.shortname}
                      </Typography>
                      <Box sx={{ pt: 1 }}>
                        <Button
                          variant="contained"
                          onClick={() =>
                            setSelectedFilters((current) => ({
                              ...current,
                              uuid: competition.uuid
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

            {resolvedCompetition && (
              <Paper
                elevation={0}
                sx={{
                  p: 1.5,
                  borderRadius: 2.5,
                  border: "1px solid rgba(20, 17, 15, 0.08)",
                  bgcolor: "teamInfo.main"
                }}
              >
                <Stack spacing={0.5}>
                  <Typography variant="subtitle2" color="text.secondary">
                    Selected UUID
                  </Typography>
                  <Typography variant="h6" sx={{ fontWeight: 700, wordBreak: "break-all" }}>
                    {resolvedCompetition.uuid}
                  </Typography>
                  <Typography color="text.secondary">
                    {resolvedCompetition.association?.name} · {resolvedCompetition.season?.name} ·{" "}
                    {formatGender(resolvedCompetition.gender)}
                  </Typography>
                  <Typography sx={{ fontWeight: 600 }}>
                    {resolvedCompetition.name}
                  </Typography>
                  <Typography color="text.secondary">
                    {resolvedCompetition.shortname}
                  </Typography>
                  <Box sx={{ pt: 1, display: "flex", alignItems: "center", gap: 1.5 }}>
                    <Button
                      variant="contained"
                      onClick={() => {
                        window.localStorage.setItem(
                          selectedCompetitionUuidStorageKey,
                          resolvedCompetition.uuid
                        );
                        navigate(`/competition/${resolvedCompetition.uuid}/teams`);
                      }}
                    >
                      Apply
                    </Button>
                    {appliedUuid === resolvedCompetition.uuid && (
                      <Typography color="text.secondary" variant="body2">
                        Saved to local storage as `competition-uuid`
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
