import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Plus } from "lucide-react";
import { useState } from "react";
import { Link, useNavigate } from "react-router";
import { postJson, type Project } from "../api/client";
import { useProjects } from "../api/queries";
import { btnPrimary, date, ErrorState, input, Panel, Q } from "../ui";

/** Create-by-name form shared by projects and models. */
export function NameForm({
  label,
  path,
  invalidate,
  onCreated,
}: {
  label: string;
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
        <label className="sr-only" htmlFor={`new-${label}`}>
          {label} name
        </label>
        <input
          id={`new-${label}`}
          className={`${input} w-64`}
          placeholder={`New ${label.toLowerCase()} name`}
          value={name}
          onChange={(e) => setName(e.target.value)}
        />
        <button className={btnPrimary} disabled={!name.trim() || m.isPending}>
          <Plus size={14} aria-hidden /> Create {label.toLowerCase()}
        </button>
      </div>
      {m.isError && <ErrorState error={m.error} />}
    </form>
  );
}

export function Projects() {
  const q = useProjects();
  const navigate = useNavigate();
  return (
    <div className="mx-auto max-w-4xl space-y-4">
      <h1 className="text-lg font-semibold">Projects</h1>
      <NameForm label="Project" path="/projects" invalidate={["projects"]} onCreated={(id) => navigate(`/projects/${id}`)} />
      <Panel title="All projects">
        <Q q={q} empty={(d) => d.length === 0 && "No projects yet. Create one above."}>
          {(projects: Project[]) => (
            <table className="w-full text-sm">
              <thead className="text-left text-xs text-muted">
                <tr>
                  <th className="py-1 font-medium">Name</th>
                  <th className="py-1 font-medium">Created</th>
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
