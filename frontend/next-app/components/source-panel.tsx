"use client"

import { type Citation } from "@/hooks/use-chat"

interface Props {
  citation: Citation | null
  query: string
}

function highlight(text: string, query: string) {
  if (!query.trim()) return [{ text, highlighted: false }]

  const words = query
    .split(/\s+/)
    .filter((w) => w.length > 3)
    .map((w) => w.replace(/[.*+?^${}()|[\]\\]/g, "\\$&"))

  if (words.length === 0) return [{ text, highlighted: false }]

  const pattern = new RegExp(`(${words.join("|")})`, "gi")
  return text.split(pattern).map((part) => ({
    text: part,
    highlighted: pattern.test(part),
  }))
}

export function SourcePanel({ citation, query }: Props) {
  if (!citation) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-4 px-8 py-10">
        <div className="flex size-14 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-100 to-violet-100 text-2xl dark:from-slate-800 dark:to-slate-700">
          📄
        </div>
        <div className="text-center space-y-1">
          <p className="text-sm font-medium">Source document</p>
          <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
            Cliquez sur une citation dans la conversation pour afficher l'extrait source utilisé
            pour formuler la réponse.
          </p>
        </div>
      </div>
    )
  }

  const parts = highlight(citation.content, query)

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-black/5 px-5 py-4 dark:border-white/5">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1.5 min-w-0">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="rounded-full bg-violet-100 px-2.5 py-0.5 text-xs font-semibold text-violet-700 dark:bg-violet-900/40 dark:text-violet-300">
                {citation.institution}
              </span>
              {citation.annee_fiscale && (
                <span className="rounded-full bg-black/5 px-2.5 py-0.5 text-xs text-muted-foreground dark:bg-white/10">
                  {citation.annee_fiscale}
                </span>
              )}
              {citation.contient_tableaux && (
                <span className="rounded-full bg-amber-100 px-2.5 py-0.5 text-xs font-medium text-amber-700 dark:bg-amber-900/30 dark:text-amber-400">
                  Tableau
                </span>
              )}
            </div>
            <p className="text-xs text-muted-foreground truncate">{citation.type_document}</p>
          </div>
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="shrink-0 rounded-lg border border-black/8 bg-white/60 px-2.5 py-1.5 text-xs font-medium text-foreground/70 transition-colors hover:bg-white hover:text-foreground dark:border-white/8 dark:bg-white/5 dark:hover:bg-white/10"
          >
            ↗ Source
          </a>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5">
        <p className="mb-3 text-[10px] font-semibold uppercase tracking-widest text-muted-foreground/60">
          Extrait utilisé
        </p>
        <div className="rounded-xl border border-black/5 bg-black/[0.02] p-4 text-sm leading-[1.75] dark:border-white/5 dark:bg-white/[0.02]">
          {parts.map((part, i) =>
            part.highlighted ? (
              <mark
                key={i}
                className="rounded-sm bg-yellow-200/80 px-0.5 text-yellow-900 dark:bg-yellow-500/25 dark:text-yellow-200"
              >
                {part.text}
              </mark>
            ) : (
              <span key={i} className="whitespace-pre-wrap text-foreground/80">
                {part.text}
              </span>
            ),
          )}
        </div>
      </div>
    </div>
  )
}
