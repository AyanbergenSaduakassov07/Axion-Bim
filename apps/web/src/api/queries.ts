import { useQuery } from "@tanstack/react-query";
import { api, type Audit, type AuditSummary, type Element, type SpatialTree, type Finding, type Job, type Model, type Project, type Revision, type RevisionSummary } from "./client";

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

export const useFindings = (auditId: number | null | undefined) =>
  useQuery({
    queryKey: ["findings", auditId],
    queryFn: () => api<Finding[]>(`/audits/${auditId}/findings`),
    enabled: auditId != null,
    staleTime: Infinity,
  });

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
