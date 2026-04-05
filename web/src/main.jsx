import React from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import {
  CssBaseline,
  ThemeProvider,
  createTheme,
  responsiveFontSizes
} from "@mui/material";
import App from "./App.jsx";
import "./index.css";

let theme = createTheme({
  palette: {
    mode: "light",
    primary: { main: "#264653" },
    secondary: { main: "#e4572e" },
    teamInfo: { main: "#fefefe" },
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
    body1: {
      fontSize: "1rem"
    },
    body2: {
      fontSize: "0.875rem"
    },
    subtitle1: {
      fontSize: "1rem"
    },
    subtitle2: {
      fontSize: "0.875rem"
    },
    h6: {
      fontSize: "1.25rem",
      fontWeight: 700
    },
    h5: {
      fontSize: "1.5rem",
      fontWeight: 700
    },
    h4: {
      fontSize: "2.125rem",
      fontWeight: 700
    }
  },
  shape: {
    borderRadius: 18
  }
});

theme = createTheme(theme, {
  typography: {
    body1: {
      [theme.breakpoints.down("md")]: {
        fontSize: "0.8rem"
      }
    },
    body2: {
      [theme.breakpoints.down("md")]: {
        fontSize: "0.7rem"
      }
    },
    subtitle1: {
      [theme.breakpoints.down("md")]: {
        fontSize: "0.8rem"
      }
    },
    subtitle2: {
      [theme.breakpoints.down("md")]: {
        fontSize: "0.7rem"
      }
    },
    h6: {
      [theme.breakpoints.down("md")]: {
        fontSize: "1rem"
      }
    },
    h5: {
      [theme.breakpoints.down("md")]: {
        fontSize: "1.2rem"
      }
    },
    h4: {
      [theme.breakpoints.down("md")]: {
        fontSize: "1.7rem"
      }
    }
  }
});

theme = responsiveFontSizes(theme);

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
