import { Chip } from "@mui/material";

function getBaseChipSx(size) {
  if (size === "small") {
    return {
      height: 20,
      fontSize: "0.6875rem",
      fontWeight: 700,
      "& .MuiChip-label": {
        px: 0.75
      }
    };
  }

  return {
    fontWeight: 700,
    letterSpacing: "0.02em"
  };
}

export function StateChip({ label, size = "small", sx = {} }) {
  return <Chip label={label} size={size} sx={{ ...getBaseChipSx(size), ...sx }} />;
}

function hasLeagueLiveStats(match) {
  if (!match || match.finished || match.results?.winner) {
    return false;
  }

  const hasSetPoints = Boolean(`${match.results?.setPoints ?? ""}`.trim());
  const hasBallPoints = Boolean(`${match.results?.ballPoints ?? ""}`.trim());
  const hasSetBallPoints = (match.results?.sets ?? []).some((set) =>
    Boolean(`${set?.ballPoints ?? ""}`.trim())
  );

  return hasSetPoints || hasBallPoints || hasSetBallPoints;
}

export function getPlannedMatchStatusChip(match) {
  const hasWinner = Boolean(match?.finished || match?.results?.winner);
  const now = Date.now();
  const matchTimestamp = new Date(
    `${match?.date ?? ""}${match?.time ? `T${match.time}` : ""}`
  ).getTime();

  if (hasWinner) {
    return {
      label: "FINISHED",
      sx: {
        bgcolor: "#e5e7eb",
        color: "#4b5563"
      }
    };
  }

  if (hasLeagueLiveStats(match)) {
    return {
      label: "LIVE",
      sx: {
        bgcolor: "#d32f2f",
        color: "#ffffff"
      }
    };
  }

  if (!Number.isNaN(matchTimestamp) && matchTimestamp > now) {
    return {
      label: "UPCOMING",
      sx: {
        bgcolor: "#fef3c7",
        color: "#c2410c"
      }
    };
  }

  return {
    label: "SCHEDULED",
    sx: {
      bgcolor: "#e5e7eb",
      color: "#4b5563"
    }
  };
}

export function getPlannedGroupStatusChip(group) {
  if (group?.finished) {
    return {
      label: "FINISHED",
      sx: {
        bgcolor: "#e5e7eb",
        color: "#4b5563"
      }
    };
  }

  return {
    label: "UPCOMING",
    sx: {
      bgcolor: "#fef3c7",
      color: "#c2410c"
    }
  };
}

export function FinishedStateChip({ finished, compact = false }) {
  return (
    <StateChip
      label={finished ? "FINISHED" : "OPEN"}
      size={compact ? "small" : "medium"}
      sx={{
        alignSelf: "flex-start",
        bgcolor: finished ? "#e5e7eb" : "#fef3c7",
        color: finished ? "#4b5563" : "#c2410c"
      }}
    />
  );
}
