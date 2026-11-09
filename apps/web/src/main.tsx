import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import "./index.css";
import { Explorer } from "./pages/Explorer";
import { Overview } from "./pages/Overview";
import { Projects } from "./pages/Projects";
import { Quality } from "./pages/Quality";
import { Upload } from "./pages/Upload";
import { Empty, Shell } from "./ui";

const client = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10_000 } } });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<Projects />} />
            <Route path="projects/:projectId" element={<Overview />} />
            <Route path="models/:modelId/upload" element={<Upload />} />
            <Route path="revisions/:revisionId/quality" element={<Quality />} />
            <Route path="revisions/:revisionId/explorer" element={<Explorer />} />
            <Route path="*" element={<Empty>Page not found.</Empty>} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  </StrictMode>,
);
