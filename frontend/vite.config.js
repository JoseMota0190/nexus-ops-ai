import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// La API vive en VITE_API_URL (por defecto http://localhost:8000).
// El backend ya tiene el CORS abierto, así que el navegador puede hablar directo.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: true,
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
