import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter, Route, Routes } from "react-router";
import "./index.css";
import { Explorer } from "./pages/Explorer";
import { Overview } from "./pages/Overview";
import { Projects } from "./pages/Projects";
import { Quality } from "./pages/Quality";
import { Quantities } from "./pages/Quantities";
import { Revisions } from "./pages/Revisions";
import { Upload } from "./pages/Upload";
import { LangProvider, useT } from "./i18n";
import { Empty, Shell } from "./ui";
import { CopilotChat } from "./copilot/CopilotChat";

function NotFound() {
  return <Empty>{useT().t("Page not found.")}</Empty>;
}

const client = new QueryClient({ defaultOptions: { queries: { retry: 1, staleTime: 10_000 } } });

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={client}>
      <LangProvider>
      <BrowserRouter>
        <Routes>
          <Route element={<Shell />}>
            <Route index element={<Projects />} />
            <Route path="projects/:projectId" element={<Overview />} />
            <Route path="projects/:projectId/copilot" element={<CopilotChat />} />
            <Route path="models/:modelId/upload" element={<Upload />} />
            <Route path="revisions/:revisionId/quality" element={<Quality />} />
            <Route path="revisions/:revisionId/explorer" element={<Explorer />} />
            <Route path="revisions/:revisionId/quantities" element={<Quantities />} />
            <Route path="models/:modelId/revisions" element={<Revisions />} />
            <Route path="*" element={<NotFound />} />
          </Route>
        </Routes>
      </BrowserRouter>
      </LangProvider>
    </QueryClientProvider>
  </StrictMode>,
);
