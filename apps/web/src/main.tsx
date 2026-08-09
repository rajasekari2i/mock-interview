import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
import { AuthProvider } from "./auth/AuthProvider";

const root = document.getElementById("root");
if (root === null) throw new Error("Application root is missing");

createRoot(root).render(
  <StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </StrictMode>
);
