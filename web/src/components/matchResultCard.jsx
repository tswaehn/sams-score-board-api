import { Box, Chip, Stack, Typography } from "@mui/material";
import { layout } from "./layout.js";

function getSetPointStyles(leftPoints, rightPoints, side) {
  const leftValue = Number(leftPoints);
  const rightValue = Number(rightPoints);

  if (Number.isNaN(leftValue) || Number.isNaN(rightValue) || leftValue === rightValue) {
    return {};
  }

  const isHigher =
    (side === "left" && leftValue > rightValue) ||
    (side === "right" && rightValue > leftValue);

  return {
    bgcolor: isHigher ? "rgba(178, 232, 187, 0.6)" : "rgba(244, 199, 199, 0.7)",
    borderRadius: 1,
    px: 0.75,
    py: 0.25,
    fontWeight: isHigher ? 700 : 400
  };
}

function TeamResultRow({
  row,
  nameColumnFraction,
  setPointWidth,
  setChipWidth,
  setSpacing,
  showBallPoints,
  ballPointWidth
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
            <Typography
              key={`${row.key}-set-${index + 1}`}
              variant="body2"
              color="text.secondary"
              sx={{
                width: setChipWidth,
                textAlign: "center",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                ...getSetPointStyles(
                  row.side === "left" ? points : opposingPoints,
                  row.side === "left" ? opposingPoints : points,
                  row.side
                )
              }}
            >
              {points}
            </Typography>
          );
        })}
        {showBallPoints && (
          <Typography
            variant="body2"
            sx={{
              width: ballPointWidth,
              textAlign: "center",
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              color: "rgba(26, 21, 18, 0.45)"
            }}
          >
            {row.ballPoints ?? "-"}
          </Typography>
        )}
      </Stack>
    </Box>
  );
}

export function MatchResultCard({
  dateLabel,
  locationLabel,
  statusChip,
  rows,
  compact = false,
  showBallPoints = true
}) {
  const nameColumnFraction = compact ? 1 : 2;
  const setChipWidth = compact ? 28 : 32;
  const setPointWidth = 32;
  const ballPointWidth = 40;
  const setSpacing = compact ? 0.5 : 1;

  return (
    <Box
      sx={{
        p: layout.padding.surface,
        borderRadius: layout.radius.surface,
        bgcolor: "background.paper",
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
          {statusChip && (
            <Chip
              label={statusChip.label}
              size="small"
              sx={{
                height: 20,
                fontSize: "0.6875rem",
                fontWeight: 700,
                "& .MuiChip-label": {
                  px: 0.75
                },
                ...statusChip.sx
              }}
            />
          )}
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
          setChipWidth={setChipWidth}
          setSpacing={setSpacing}
          showBallPoints={showBallPoints}
          ballPointWidth={ballPointWidth}
        />
      ))}
    </Box>
  );
}
