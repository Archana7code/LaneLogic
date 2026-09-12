import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

// LaneLogic - PERSON 6: Frontend/Dashboard
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // lets pages import Person 5's map component directly from the
      // sibling person5_gis folder without a messy relative path.
      "@person5": path.resolve(__dirname, "../person5_gis"),
    },
  },
  server: {
    port: 5173,
  },
});
