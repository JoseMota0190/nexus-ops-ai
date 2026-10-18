import React from "react";
import { createRoot } from "react-dom/client";
import App from "./App.jsx";
import { idiomaGuardado } from "./i18n.js";
import "./styles.css";

idiomaGuardado(); // the chosen language, before the very first render

createRoot(document.getElementById("root")).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
);
