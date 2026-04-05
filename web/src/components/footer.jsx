import { useLocation } from "react-router-dom";
import { Box, Container, Link, Typography } from "@mui/material";
import {
  getEntityConfig,
  getEntityFromPath,
  isEmbeddedSearch
} from "../entities/entity.js";

export default function Footer() {
  const location = useLocation();
  const isEmbedded = isEmbeddedSearch(location.search);
  const { entityType, entityUuid } = getEntityFromPath(location.pathname);
  const entityLabel = entityType ? getEntityConfig(entityType).singularLabel : "";

  return (
    <Box
      component="footer"
      sx={{
        px: 3,
        py: 2.5,
        borderTop: "1px solid rgba(20, 17, 15, 0.08)",
        bgcolor: "rgba(255, 255, 255, 0.7)"
      }}
    >
      <Container sx={{ display: "flex", justifyContent: "center" }}>
        <Box sx={{ display: "grid", justifyItems: "center", gap: 0.5 }}>
          {!isEmbedded && (
            <Box sx={{ display: "flex", gap: 2 }}>
              <Link
                href="/competitions"
                color="text.secondary"
                underline="hover"
                sx={{ fontWeight: 500 }}
              >
                Competition List
              </Link>
              <Link
                href="/leagues"
                color="text.secondary"
                underline="hover"
                sx={{ fontWeight: 500 }}
              >
                League List
              </Link>
            </Box>
          )}
          {entityUuid && (
            <Typography
              variant="body2"
              sx={{ color: "rgba(20, 17, 15, 0.45)", fontWeight: 300, textAlign: "center" }}
            >
              {entityLabel}
              <br />
              {entityUuid}
            </Typography>
          )}
        </Box>
      </Container>
    </Box>
  );
}
