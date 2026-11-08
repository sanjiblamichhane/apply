import { TooltipProvider } from "@apply/ui";
import { createRoot } from "react-dom/client";

import { followTheme } from "../theme";
import { App } from "./App";

// Match the system, Light or Dark, as chosen in Settings (the system's by default).
followTheme();

createRoot(document.getElementById("root")!).render(
  <TooltipProvider delayDuration={300}>
    <App />
  </TooltipProvider>,
);
