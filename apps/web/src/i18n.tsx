import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { kk } from "./i18n-kk";
import { ru } from "./i18n-ru";

/** UI strings are keyed by their English text; a missing Kazakh entry falls back to Russian, a missing Russian one to English. */
export type Lang = "en" | "ru" | "kk";
export const LANGS: Lang[] = ["en", "ru", "kk"];
type Vars = Record<string, string | number>;
export type T = (text: string, vars?: Vars) => string;

const KEY = "axiom.lang";

function initialLang(): Lang {
  try {
    const saved = localStorage.getItem(KEY);
    if (LANGS.includes(saved as Lang)) return saved as Lang;
  } catch {
    // storage blocked (private mode): fall through to the browser language
  }
  const nav = navigator.language.toLowerCase();
  return nav.startsWith("kk") ? "kk" : nav.startsWith("ru") ? "ru" : "en";
}

let active: Lang = "en";
/** Number and date formatting outside React (fmt helpers) follows the language picked in the UI. */
export const locale = () => ({ en: "en-US", ru: "ru-RU", kk: "kk-KZ" })[active];

// shortcut: backend texts (rule messages, reports) exist in en/ru only; Kazakh UI asks for Russian ones. Add kk to axiom.i18n when a client needs it.
export const backendLang = (lang: Lang) => (lang === "kk" ? "ru" : lang);

export const translate = (lang: Lang, text: string, vars?: Vars) =>
  (lang === "kk" ? (kk[text] ?? ru[text] ?? text) : lang === "ru" ? (ru[text] ?? text) : text).replace(/\{(\w+)\}/g, (m: string, k: string) => (vars && k in vars ? String(vars[k]) : m));

const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void; t: T }>({
  lang: "en",
  setLang: () => {},
  t: (text, vars) => translate("en", text, vars),
});

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(initialLang);
  active = lang; // set during render so children format numbers in the same pass
  useEffect(() => {
    document.documentElement.lang = lang;
    try {
      localStorage.setItem(KEY, lang);
    } catch {
      // not persisted; the choice still holds for this session
    }
  }, [lang]);
  return <Ctx.Provider value={{ lang, setLang, t: (text, vars) => translate(lang, text, vars) }}>{children}</Ctx.Provider>;
}

export const useT = () => useContext(Ctx);

/** Machine tokens from the backend (statuses, events, dimensions, notes): `not_evaluated` -> "not evaluated", then translated. */
export const tokenLabel = (t: T, token: string) => t(token.replace(/_/g, " "));
