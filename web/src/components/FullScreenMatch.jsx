import { Box, Typography } from "@mui/material";
import { getTeamShortName } from "../api/api.js";
import { BallPoint } from "./ballPoint.jsx";
import { layout } from "./layout.js";
import { StatusChip } from "./stateChip.jsx";

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

function TeamRow({ row }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr) 20px auto",
        alignItems: "center",
        columnGap: 0.5
      }}
    >
      <Typography
        variant="body2"
        sx={{
          minWidth: 0,
          fontWeight: row.isWinner ? 700 : 500,
          whiteSpace: "nowrap",
          overflow: "hidden",
          textOverflow: "ellipsis",
          fontSize: "0.8rem",
          lineHeight: 1.2
        }}
      >
        {getTeamShortName(row.teamName ?? "", row.teamShortName, 20)}
      </Typography>

      <Typography
        variant="body2"
        sx={{
          textAlign: "center",
          fontWeight: row.isWinner ? 700 : 500,
          fontSize: "0.8rem",
          lineHeight: 1.2
        }}
      >
        {row.totalSetPoints ?? "-"}
      </Typography>

      <Box
        sx={{
          display: "inline-flex",
          justifyContent: "flex-end",
          gap: 0.25,
          minWidth: 0
        }}
      >
        {row.setPoints.map((points, index) => {
          const opposingPoints = row.opponentSetPoints[index] ?? "-";
          const defaultState = getSetPointStyles(
            row.side === "left" ? points : opposingPoints,
            row.side === "left" ? opposingPoints : points,
            row.side
          );

          return (
            <BallPoint
              key={`${row.key}-set-${index + 1}`}
              value={points}
              size="tinySet"
              state={defaultState}
            />
          );
        })}
      </Box>
    </Box>
  );
}

export default function FullScreenMatch({
  dateLabel,
  statusChip,
  rows
}) {
  return (
    <Box
      sx={{
        minWidth: 0,
        p: 0.5,
        borderRadius: 0.5,
        border: "1px solid rgba(20, 17, 15, 0.08)",
        bgcolor: "background.paper",
        display: "grid",
        gap: 0.5
      }}
    >
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 0.5
        }}
      >
        <Typography
          variant="body2"
          sx={{
            color: "rgba(26, 21, 18, 0.45)",
            fontSize: "0.74rem",
            lineHeight: 1.1
          }}
        >
          {dateLabel}
        </Typography>
        {statusChip && <StatusChip type={statusChip} size="xsmall" />}
      </Box>

      <Box sx={{ display: "grid", gap: 0.35 }}>
        {rows.map((row) => (
          <TeamRow key={row.key} row={row} />
        ))}
      </Box>
    </Box>
  );
}
