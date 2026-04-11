import { Box, Stack, Typography } from "@mui/material";
import { BallPoint } from "./ballPoint.jsx";
import { layout } from "./layout.js";
import {
  FinishedStateChip,
  StatusChip
} from "./stateChip.jsx";

function getSetPointStyles(leftPoints, rightPoints, side) {
  const leftValue = Number(leftPoints);
  const rightValue = Number(rightPoints);

  if (Number.isNaN(leftValue) || Number.isNaN(rightValue) || leftValue === rightValue) {
    return "default";
  }

  const isHigher =
    (side === "left" && leftValue > rightValue) ||
    (side === "right" && rightValue > leftValue);

  return isHigher ? "won" : "lost";
}

function TeamResultRow({
  row,
  nameColumnFraction,
  setPointWidth,
  setSpacing,
  showBallPoints,
  compact
}) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: `minmax(0, ${nameColumnFraction}fr) ${setPointWidth}px minmax(0, 1fr)`,
        alignItems: "center",
        columnGap: { xs: 1, sm: 1.5 }
      }}
    >
      <Typography sx={{ fontWeight: row.isWinner ? 700 : 500 }}>
        {row.label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          width: setPointWidth,
          textAlign: "center",
          display: "inline-flex",
          alignItems: "center",
          justifyContent: "center",
          fontWeight: 700
        }}
      >
        {row.totalSetPoints ?? "-"}
      </Typography>
      <Stack direction="row" spacing={setSpacing} justifyContent="flex-end" sx={{ justifySelf: "end" }}>
        {row.setPoints.map((points, index) => {
          const opposingPoints = row.opponentSetPoints[index] ?? "-";

          return (
            <BallPoint
              key={`${row.key}-set-${index + 1}`}
              value={points}
              size={compact ? "compactSet" : "set"}
              state={getSetPointStyles(
                row.side === "left" ? points : opposingPoints,
                row.side === "left" ? opposingPoints : points,
                row.side
              )}
            />
          );
        })}
        {showBallPoints && (
          <BallPoint
            value={row.ballPoints}
            size="total"
            state="muted"
          />
        )}
      </Stack>
    </Box>
  );
}

export function MatchResultCard({
  dateLabel,
  locationLabel,
  statusChip,
  finished,
  rows,
  compact = false,
  showBallPoints = true
}) {
  const nameColumnFraction = compact ? 1 : 2;
  const setPointWidth = 32;
  const setSpacing = compact ? 0.5 : 1;
  const isFinishedStatusChip = statusChip === "FINISHED";
  const showFinishedChip = typeof finished === "boolean" && !isFinishedStatusChip;

  return (
    <Box
      sx={{
        p: layout.padding.surface,
        borderRadius: layout.radius.surface,
        bgcolor: "#ffffff",
        display: "grid",
        gap: layout.gap.surface
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "flex-start", sm: "center" }}
        spacing={0.5}
      >
        <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
          <Typography sx={{ fontWeight: 600, color: "rgba(26, 21, 18, 0.45)" }}>
            {dateLabel}
          </Typography>
          {statusChip && !isFinishedStatusChip && (
            <StatusChip type={statusChip} size="small" />
          )}
          {isFinishedStatusChip && <FinishedStateChip finished compact />}
          {showFinishedChip && <FinishedStateChip finished={finished} compact />}
        </Stack>
        {locationLabel && (
          <Typography sx={{ color: "rgba(26, 21, 18, 0.45)" }}>
            {locationLabel}
          </Typography>
        )}
      </Stack>

      {rows.map((row) => (
        <TeamResultRow
          key={row.key}
          row={row}
          nameColumnFraction={nameColumnFraction}
          setPointWidth={setPointWidth}
          setSpacing={setSpacing}
          showBallPoints={showBallPoints}
          compact={compact}
        />
      ))}
    </Box>
  );
}
