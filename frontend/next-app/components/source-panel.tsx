"use client"

import dynamic from "next/dynamic"
import { useEffect, useState } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  DocumentValidationIcon,
  TouchInteraction01Icon,
} from "@hugeicons/core-free-icons"
import { type Citation } from "@/hooks/use-chat"
import { cn } from "@/lib/utils"

const PdfViewer = dynamic(
  () => import("@/components/pdf-viewer").then((m) => m.PdfViewer),
  { ssr: false },
)

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
  const hasPdf = Boolean(citation?.url_hash && citation?.page_start != null)
  const [tab, setTab] = useState<"text" | "pdf">(hasPdf ? "pdf" : "text")

  useEffect(() => {
    setTab(Boolean(citation?.url_hash && citation?.page_start != null) ? "pdf" : "text")
  }, [citation?.url_hash])

  if (!citation) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-5 px-8 py-10">
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-orange-50 to-violet-50 p-5 dark:from-slate-800 dark:to-slate-700">
          <img
            src="https://images.unsplash.com/photo-1568234928966-359c35dd8327?w=160&h=120&fit=crop&q=80"
            alt="Documents publics"
            className="size-20 rounded-xl object-cover opacity-80"
          />
          <div className="absolute bottom-2 right-2 rounded-lg bg-white/90 p-1.5 shadow-sm dark:bg-slate-900/90">
            <HugeiconsIcon
              icon={DocumentValidationIcon}
              size={14}
              className="text-violet-500"
              strokeWidth={2}
            />
          </div>
        </div>

        <div className="text-center space-y-1.5">
          <p className="text-sm font-medium">Source document</p>
          <p className="text-xs text-muted-foreground max-w-xs leading-relaxed">
            Cliquez sur une citation dans la conversation pour afficher l'extrait utilisé.
          </p>
        </div>

        <div className="flex items-center gap-1.5 rounded-full border border-black/8 bg-black/[0.02] px-3 py-1.5 text-xs text-muted-foreground dark:border-white/8 dark:bg-white/[0.03]">
          <HugeiconsIcon icon={TouchInteraction01Icon} size={12} strokeWidth={2} />
          <span>
            Cliquez sur{" "}
            <strong className="font-semibold text-foreground/70">↗ Source N</strong> dans le chat
          </span>
        </div>
      </div>
    )
  }

  const parts = highlight(citation.content, query)
  const pdfUrl = `${process.env.NEXT_PUBLIC_API_URL}/api/v1/pdfs/${citation.url_hash}`

  return (
    <div className="flex h-full flex-col">
      {/* Header */}
      <div className="border-b border-black/5 px-5 py-4 dark:border-white/5">
        <div className="flex items-start gap-3">
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
              {citation.page_start != null && (
                <span className="rounded-full bg-black/5 px-2.5 py-0.5 text-xs text-muted-foreground dark:bg-white/10">
                  p.{citation.page_start}
                  {citation.page_end !== citation.page_start ? `–${citation.page_end}` : ""}
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
        </div>

        {/* Tabs */}
        {hasPdf && (
          <div className="mt-3 flex gap-1">
            {(["text", "pdf"] as const).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={cn(
                  "rounded-lg px-3 py-1 text-xs font-medium transition-colors",
                  tab === t
                    ? "bg-violet-100 text-violet-700 dark:bg-violet-900/40 dark:text-violet-300"
                    : "text-muted-foreground hover:text-foreground",
                )}
              >
                {t === "text" ? "Extrait" : "PDF"}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div className={cn("flex-1", tab === "pdf" && hasPdf ? "overflow-hidden" : "overflow-y-auto px-5 py-5")}>
        {tab === "text" || !hasPdf ? (
          <>
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
          </>
        ) : (
          <PdfViewer
            pdfUrl={pdfUrl}
            pageStart={citation.page_start!}
          />
        )}
      </div>
    </div>
  )
}
