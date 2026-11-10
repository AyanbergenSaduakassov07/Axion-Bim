// Thin fetch client. Types are generated from the backend OpenAPI (npm run gen:api).
import type { components } from "./schema";

type S = components["schemas"];
export type Project = S["ProjectOut"];
export type Model = S["ModelOut"];
export type Revision = S["RevisionOut"];
export type RevisionSummary = S["RevisionSummary"];
export type Audit = S["AuditOut"];
export type Finding = S["Finding"];
export type Job = S["JobOut"];
export type SpatialTree = S["SpatialTree"];
export type TreeElement = S["TreeElement"];
export type Element = S["Element"];
export type Change = S["ChangeOut"];
export type FindingEvent = S["FindingEvent"];
export type CopilotStatus = S["CopilotStatus"];
export type CopilotAnswer = S["CopilotAnswer"];
export type Citation = S["CitationOut"];
export type Issue = S["IssueOut"];
export type Dashboard = S["Dashboard"];
export type IssueUpdate = S["IssueUpdate"];
export type IdsEntry = S["IdsEntry"];

export type ComparisonSummary = {
  changes: Record<string, number>;
  changes_by_class: Record<string, Record<string, number>>;
  events: Record<string, number>;
  mhi: { base: number | null; head: number | null; delta: number | null; dimensions: Record<string, number> };
  impact: { global_id: string; element_name: string | null; rule_id: string; event: string; paths: string[] }[];
  ids_mismatch: boolean;
  ruleset_mismatch: boolean;
  unstable_classes: string[];
  uncertain_global_ids: string[];
};
export type Comparison = Omit<S["ComparisonOut"], "summary_json"> & { summary_json: ComparisonSummary };

type QuantityKey = { group: string; qto: string; quantity: string; method: "qto" | "geometry"; unit: string | null };
export type QuantityRow = QuantityKey & { total: number; count: number; missing: string[] };
export type QuantityDelta = QuantityKey & { old: number | null; new: number | null };
export type Quantities = { rows: QuantityRow[]; delta: QuantityDelta[] };

export type Dimension = {
  score: number | null;
  passed: number;
  failed: number;
  warnings: number;
  not_evaluated: number;
  errors: number;
  weight: number;
  effective_weight: number;
  contribution: number;
};
export type Mhi = {
  score: number | null;
  coverage: number | null;
  blocked: boolean;
  blocking: string[];
  dimensions: Record<string, Dimension>;
  notes: string[];
  config_version: string;
};
export type RuleMeta = { id: string; version: string; name: string; description: string; dimension: string };
export type AuditSummary = {
  mhi: Mhi;
  rules: RuleMeta[];
  reproducibility: Record<string, unknown>;
};

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

const BASE = "/api/v1";

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(BASE + path, init);
  } catch {
    throw new ApiError(0, "network", "The Axiom API is not reachable. Is `axiom serve` running?");
  }
  const body = await res.json().catch(() => null);
  if (!res.ok) {
    const err = body?.error ?? {};
    throw new ApiError(res.status, err.code ?? `http_${res.status}`, err.message ?? res.statusText);
  }
  return body as T;
}

export const postJson = <T>(path: string, data: unknown) =>
  api<T>(path, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });

export const putJson = <T>(path: string, data: unknown) =>
  api<T>(path, { method: "PUT", headers: { "content-type": "application/json" }, body: JSON.stringify(data) });

export const postForm = <T>(path: string, form: FormData) => api<T>(path, { method: "POST", body: form });
