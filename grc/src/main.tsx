import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App";
import { applyStoredTheme } from "./theme";

// Paint with the last known theme; the bootstrap response confirms or replaces it.
applyStoredTheme();
createRoot(document.getElementById("root")!).render(<App />);
import "./public.css";

import "./portal-controls.css";
