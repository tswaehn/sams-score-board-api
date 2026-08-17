import { Typography } from "@mui/material";

const BALL_POINT_STYLES = {
  default: {},
  muted: {
    color: "rgba(26, 21, 18, 0.45)"
  },
  won: {
    bgcolor: "rgba(178, 232, 187, 0.6)",
    borderRadius: 1,
    px: 0.75,
    py: 0.25,
    fontWeight: 700
  },
  lost: {
    bgcolor: "rgba(244, 199, 199, 0.7)",
    borderRadius: 1,
    px: 0.75,
    py: 0.25,
    fontWeight: 400
  },
  active: {
    bgcolor: "#e5e7eb",
    borderRadius: 1,
    px: 0.75,
    py: 0.25
  },
  activeServing: {
    bgcolor: "#e5e7eb",
    borderRadius: 1,
    px: 0.75,
    py: 0.25,
    fontWeight: 700,
    border: "1px solid #4b5563"
  }
};

const BALL_POINT_SIZES = {
  set: 32,
  compactSet: 28,
  tinySet: 22,
  total: 40
};

export function BallPoint({ value, state = "default", size = "set" }) {
  return (
    <Typography
      variant={size === "tinySet" ? "caption" : "body2"}
      sx={{
        width: BALL_POINT_SIZES[size] ?? BALL_POINT_SIZES.set,
        textAlign: "center",
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        fontSize: size === "tinySet" ? "0.65rem" : undefined,
        lineHeight: size === "tinySet" ? 1.1 : undefined,
        ...BALL_POINT_STYLES[state]
      }}
    >
      {value ?? "-"}
    </Typography>
  );
}
