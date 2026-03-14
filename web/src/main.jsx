import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { CssBaseline, ThemeProvider, createTheme } from "@mui/material";
import App from "./App.jsx";
import "./index.css";

const theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#264653" },
    secondary: { main: "#e4572e" },
    background: {
      default: "#ffffff",
      paper: "#f8f4ee"
    },
    text: {
      primary: "#1a1512",
      secondary: "#4b4039"
    }
  },
  typography: {
    fontFamily: '"Space Grotesk", "Segoe UI", sans-serif',
    h6: { fontWeight: 700 },
    h5: { fontWeight: 700 },
    h4: { fontWeight: 700 }
  },
  shape: {
    borderRadius: 18
  }
});

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ThemeProvider>
  </React.StrictMode>
);
