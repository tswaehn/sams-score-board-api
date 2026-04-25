import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  build: {
    // Keep the shipped bundle compatible with older module-capable browsers.
    target: "es2017"
  }
});
