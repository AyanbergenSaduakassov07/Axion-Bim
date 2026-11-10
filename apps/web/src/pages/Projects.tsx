import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { postJson, type Project } from "../api/client";
import { useProjects } from "../api/queries";
import { useT } from "../i18n";
import { btnPrimary, date, ErrorState, input, Panel, Q } from "../ui";

/** Create-by-name form shared by projects and models. */
export function NameForm({
  label,
  placeholder,
  submit: submitLabel,
  path,
  invalidate,
  onCreated,
}: {
  label: string;
  placeholder: string;
  submit: string;
  path: string;
  invalidate: unknown[];
  onCreated?: (id: number) => void;
}) {
  const [name, setName] = useState("");
  const qc = useQueryClient();
  const m = useMutation({
    mutationFn: (n: string) => postJson<{ id: number }>(path, { name: n }),
    onSuccess: (created) => {
      setName("");
      qc.invalidateQueries({ queryKey: invalidate });
      onCreated?.(created.id);
    },
  });
  const submit = (e: { preventDefault(): void }) => {
    e.preventDefault();
    if (name.trim()) m.mutate(name.trim());
  };
  return (
    <form onSubmit={submit} className="space-y-2">
      <div className="flex gap-2">
        <label className="sr-only" htmlFor={`new-${path}`}>
          {label}
        </label>
        <input
          id={`new-${path}`}
          className={`${input} w-64`}
          placeholder={placeholder}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button className={btnPrimary} disabled={!name.trim() || m.isPending}>
          <Plus size={14} aria-hidden /> {submitLabel}
        </button>
      </div>
      {m.isError && <ErrorState error={m.error} />}
    </form>
  );
}

export function Projects() {
  const q = useProjects();
  const navigate = useNavigate();
  const { t } = useT();
  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <h1 className="text-lg font-semibold">{t("Projects")}</h1>
      <NameForm label={t("Project name")} placeholder={t("New project name")} submit={t("Create project")} path="/projects" invalidate={["projects"]} onCreated={(id) => navigate(`/projects/${id}`)} />
      <Panel title={t("All projects")}>
        <Q q={q} empty={(d) => d.length === 0 && t("No projects yet. Create one above.")}>
          {(projects: Project[]) => (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted">
                <tr>
                  <th className="py-1 font-medium">{t("Name")}</th>
                  <th className="py-1 font-medium">{t("Created")}</th>
                </tr>
              </thead>
              <tbody>
                {projects.map((p) => (
                  <tr key={p.id} className="border-t border-line">
                    <td className="py-1.5">
                      <Link className="text-accent hover:underline" to={`/projects/${p.id}`}>
                        {p.name}
                      </Link>
                    </td>
                    <td className="py-1.5 text-muted">{date(p.created_at)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Q>
      </Panel>
    </div>
  );
}
