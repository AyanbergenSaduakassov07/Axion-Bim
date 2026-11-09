export type Part = { kind: "text"; text: string } | { kind: "cite"; type: "element" | "finding"; id: string };

const MARK = /\[\[(el|finding):([^\]\s]+)\]\]/g; // same markup the backend post-check verifies

export function splitCitations(text: string): Part[] {
  const parts: Part[] = [];
  let last = 0;
  for (const m of text.matchAll(MARK)) {
    if (m.index > last) parts.push({ kind: "text", text: text.slice(last, m.index) });
    parts.push({ kind: "cite", type: m[1] === "el" ? "element" : "finding", id: m[2] });
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push({ kind: "text", text: text.slice(last) });
  return parts;
}
