import { useT } from "../i18n";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, postForm, postJson, putJson, type IdsEntry, type Dashboard, type Issue, type IssueUpdate, type CopilotAnswer, type CopilotStatus, type Audit, type Change, type Comparison, type FindingEvent, type Quantities, type AuditSummary, type Element, type SpatialTree, type Finding, type Job, type Model, type Project, type Revision, type RevisionSummary } from "./client";

export const useProjects = () => useQuery({ queryKey: ["projects"], queryFn: () => api<Project[]>("/projects") });

export const useModels = (projectId: number) =>
  useQuery({ queryKey: ["models", projectId], queryFn: () => api<Model[]>(`/projects/${projectId}/models`) });

export const useRevisions = (modelId: number | undefined) =>
  useQuery({
    queryKey: ["revisions", modelId],
    queryFn: () => api<Revision[]>(`/models/${modelId}/revisions`),
    enabled: modelId != null,
  });

export const useRevision = (revisionId: number | undefined) =>
  useQuery({
    queryKey: ["revision", revisionId],
    queryFn: () => api<RevisionSummary>(`/revisions/${revisionId}`),
    enabled: revisionId != null,
  });

export const useAudits = (revisionId: number) =>
  useQuery({ queryKey: ["audits", revisionId], queryFn: () => api<Audit[]>(`/revisions/${revisionId}/audits`) });

export const useAuditSummary = (auditId: number | null | undefined) =>
  useQuery({
    queryKey: ["audit", auditId],
    queryFn: () => api<AuditSummary>(`/audits/${auditId}`),
    enabled: auditId != null,
    staleTime: Infinity, // audit runs are immutable
  });

export const useFindings = (auditId: number | null | undefined) => {
  const { lang } = useT(); // rule texts are translated by the backend
  return useQuery({
    queryKey: ["findings", auditId, lang],
    queryFn: () => api<Finding[]>(`/audits/${auditId}/findings?lang=${lang}`),
    enabled: auditId != null,
    staleTime: Infinity,
  });
};

const RUNNING = new Set(["queued", "running"]);

export const useJob = (jobId: number | undefined) =>
  useQuery({
    queryKey: ["job", jobId],
    queryFn: () => api<Job>(`/jobs/${jobId}`),
    enabled: jobId != null,
    refetchInterval: (q) => (q.state.data && !RUNNING.has(q.state.data.status) ? false : 1000),
  });

export const useTree = (revisionId: number) =>
  useQuery({
    queryKey: ["tree", revisionId],
    queryFn: () => api<SpatialTree>(`/revisions/${revisionId}/tree`),
    staleTime: Infinity, // revisions are immutable
  });

export const useElement = (revisionId: number, globalId: string | null) =>
  useQuery({
    queryKey: ["element", revisionId, globalId],
    queryFn: () => api<Element>(`/revisions/${revisionId}/elements/${encodeURIComponent(globalId!)}`),
    enabled: globalId != null,
    staleTime: Infinity,
  });

export const useComparisons = (revisionId: number | undefined) =>
  useQuery({
    queryKey: ["comparisons", revisionId],
    queryFn: () => api<Comparison[]>(`/revisions/${revisionId}/comparisons`),
    enabled: revisionId != null,
  });

// comparisons are immutable once written
export const useChanges = (comparisonId: number) =>
  useQuery({ queryKey: ["changes", comparisonId], queryFn: () => api<Change[]>(`/comparisons/${comparisonId}/changes`), staleTime: Infinity });

export const useEvents = (comparisonId: number) =>
  useQuery({ queryKey: ["events", comparisonId], queryFn: () => api<FindingEvent[]>(`/comparisons/${comparisonId}/events`), staleTime: Infinity });

export const useQuantities = (revisionId: number, by: string, against: number | undefined) =>
  useQuery({
    queryKey: ["quantities", revisionId, by, against],
    queryFn: () => api<Quantities>(`/revisions/${revisionId}/quantities?by=${by}${against != null ? `&against=${against}` : ""}`),
    staleTime: Infinity,
  });

export const useCopilotStatus = () =>
  useQuery({ queryKey: ["copilot"], queryFn: () => api<CopilotStatus>("/copilot"), staleTime: Infinity });

export const useCopilotAsk = (projectId: number) =>
  useMutation({
    mutationFn: ({ question, history = [] }: { question: string; history?: { question: string; answer: string }[] }) =>
      postJson<CopilotAnswer>("/copilot/query", { project_id: projectId, question, history }),
  });

export const useIssues = (modelId: number | undefined) =>
  useQuery({ queryKey: ["issues", modelId], queryFn: () => api<Issue[]>(`/models/${modelId}/issues`), enabled: modelId != null });

export function useUpdateIssues(modelId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: IssueUpdate) => putJson<{ updated: number }>(`/models/${modelId}/issues`, body),
    onSuccess: () => Promise.all([qc.invalidateQueries({ queryKey: ["issues", modelId] }), qc.invalidateQueries({ queryKey: ["dashboard"] })]),
  });
}

export const useDashboard = (projectId: number) =>
  useQuery({ queryKey: ["dashboard", projectId], queryFn: () => api<Dashboard>(`/projects/${projectId}/dashboard`) });

export const useModel = (modelId: number) => useQuery({ queryKey: ["model", modelId], queryFn: () => api<Model>(`/models/${modelId}`) });

export const useIdsLibrary = (projectId: number | undefined) =>
  useQuery({ queryKey: ["ids", projectId], queryFn: () => api<IdsEntry[]>(`/projects/${projectId}/ids`), enabled: projectId != null });

export const addIds = (projectId: number, file: File) => {
  const form = new FormData();
  form.append("file", file);
  form.append("name", file.name.replace(/\.(ids|xml)$/i, ""));
  return postForm<IdsEntry>(`/projects/${projectId}/ids`, form);
};

export function useIdsMutations(projectId: number) {
  const qc = useQueryClient();
  const refresh = () => qc.invalidateQueries({ queryKey: ["ids", projectId] });
  return {
    add: useMutation({ mutationFn: (file: File) => addIds(projectId, file), onSuccess: refresh }),
    setDefault: useMutation({
      mutationFn: ({ id, is_default }: { id: number; is_default: boolean }) =>
        putJson<IdsEntry[]>(`/projects/${projectId}/ids/${id}/default`, { is_default }),
      onSuccess: refresh,
    }),
  };
}
