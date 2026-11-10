// Just enough markdown for model answers (paragraphs, lists, headings, bold, code). No HTML is ever produced
// from the text: the renderer maps these parts to React elements, so model output cannot inject markup.
export type Block = { kind: "p" | "ul" | "ol" | "h"; lines: string[] };
export type Span = { kind: "text" | "b" | "code"; text: string };

const UL = /^\s*[-*•]\s+(.*)$/;
const OL = /^\s*\d+[.)]\s+(.*)$/;
const H = /^#{1,6}\s+(.*)$/;

export function blocks(text: string): Block[] {
  const out: Block[] = [];
  for (const raw of text.split("\n")) {
    const line = raw.trimEnd();
    const m = line.match(UL) ?? line.match(OL) ?? line.match(H);
    const kind = !line.trim() ? null : UL.test(line) ? "ul" : OL.test(line) ? "ol" : H.test(line) ? "h" : "p";
    const last = out.at(-1);
    if (kind == null) out.push({ kind: "p", lines: [] }); // blank line ends the block
    else if (last && last.kind === kind && kind !== "h" && (kind !== "p" || last.lines.length)) last.lines.push(m?.[1] ?? line);
    else out.push({ kind, lines: [m?.[1] ?? line] });
  }
  return out.filter((b) => b.lines.length);
}

const INLINE = /\*\*([^*]+)\*\*|`([^`]+)`/g;

export function inline(text: string): Span[] {
  const out: Span[] = [];
  let last = 0;
  for (const m of text.matchAll(INLINE)) {
    if (m.index > last) out.push({ kind: "text", text: text.slice(last, m.index) });
    out.push(m[1] != null ? { kind: "b", text: m[1] } : { kind: "code", text: m[2] });
    last = m.index + m[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}
