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

export const postForm = <T>(path: string, form: FormData) => api<T>(path, { method: "POST", body: form });
