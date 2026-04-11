import { Box, Chip } from "@mui/material";

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

function BaseStateChip({ label, size = "small", chipSx }) {
  return <Chip label={label} size={size} sx={{ ...getBaseChipSx(size), ...chipSx }} />;
}

export function FinishedChip({ size = "small" }) {
  return (
    <BaseStateChip
      label="FINISHED"
      size={size}
      chipSx={{
        bgcolor: "#e5e7eb",
        color: "#4b5563"
      }}
    />
  );
}

export function LiveChip({ size = "small" }) {
  return (
    <BaseStateChip
      label="LIVE"
      size={size}
      chipSx={{
        bgcolor: "#d32f2f",
        color: "#ffffff"
      }}
    />
  );
}

export function UpcomingChip({ size = "small" }) {
  return (
    <BaseStateChip
      label="UPCOMING"
      size={size}
      chipSx={{
        bgcolor: "#fef3c7",
        color: "#c2410c"
      }}
    />
  );
}

export function ScheduledChip({ size = "small" }) {
  return (
    <BaseStateChip
      label="SCHEDULED"
      size={size}
      chipSx={{
        bgcolor: "#fef3c7",
        color: "#c2410c"
      }}
    />
  );
}

export function StatusChip({ type, size = "small" }) {
  if (type === "FINISHED") {
    return <FinishedChip size={size} />;
  }

  if (type === "LIVE") {
    return <LiveChip size={size} />;
  }

  if (type === "UPCOMING") {
    return <UpcomingChip size={size} />;
  }

  return <ScheduledChip size={size} />;
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
    return "FINISHED";
  }

  if (hasLeagueLiveStats(match)) {
    return "LIVE";
  }

  if (!Number.isNaN(matchTimestamp) && matchTimestamp > now) {
    return "UPCOMING";
  }

  return "SCHEDULED";
}

export function getPlannedGroupStatusChip(group) {
  if (group?.finished) {
    return "FINISHED";
  }

  return "SCHEDULED";
}

export function getCompetitionStatusChip(matchState) {
  if (matchState?.finished) {
    return "FINISHED";
  }

  if (matchState?.started) {
    return "LIVE";
  }

  return "SCHEDULED";
}

export function FinishedStateChip({ finished, compact = false }) {
  return (
    <Box sx={{ alignSelf: "flex-start" }}>
      <StatusChip type={finished ? "FINISHED" : "SCHEDULED"} size={compact ? "small" : "medium"} />
    </Box>
  );
}
