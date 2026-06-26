"use client"

import { useEffect, useRef, useState } from "react"
import { Button } from "@/components/ui/button"
import { type Citation, type Message } from "@/hooks/use-chat"
import { cn } from "@/lib/utils"

interface Props {
  messages: Message[]
  isStreaming: boolean
  onSend: (question: string) => void
  onCitationClick: (citation: Citation, question: string) => void
}

function parseContent(
  content: string,
  citations: Citation[],
  onCitationClick: (c: Citation) => void,
) {
  const parts = content.split(/(\[Source \d+\])/g)
  return parts.map((part, i) => {
    const match = part.match(/\[Source (\d+)\]/)
    if (match) {
      const idx = parseInt(match[1])
      const citation = citations.find((c) => c.index === idx)
      if (citation) {
        return (
          <button
            key={i}
            onClick={() => onCitationClick(citation)}
            className="mx-0.5 inline-flex items-baseline gap-1 rounded-full bg-violet-100 px-2 py-0.5 text-[11px] font-semibold text-violet-700 transition-colors hover:bg-violet-200 dark:bg-violet-900/40 dark:text-violet-300 dark:hover:bg-violet-800/60"
          >
            <span className="leading-none">↗</span>
            {citation.institution.split(" ")[0]} {idx}
          </button>
        )
      }
    }
    return (
      <span key={i} className="whitespace-pre-wrap">
        {part}
      </span>
    )
  })
}

const SUGGESTIONS = [
  "Quel est le budget de l'État pour 2026 ?",
  "Quelles sont les recettes fiscales prévues ?",
  "Comment évolue la dette publique ?",
]

export function ChatPanel({ messages, isStreaming, onSend, onCitationClick }: Props) {
  const [input, setInput] = useState("")
  const bottomRef = useRef<HTMLDivElement>(null)
  const lastQuestion = useRef("")

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const q = input.trim()
    if (!q) return
    lastQuestion.current = q
    setInput("")
    onSend(q)
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-b border-black/5 px-5 py-4 dark:border-white/5">
        <div className="flex items-center gap-2.5">
          <span className="flex size-7 items-center justify-center rounded-lg bg-gradient-to-br from-orange-400 to-violet-500 text-sm font-bold text-white shadow-sm">
            R
          </span>
          <div>
            <h1 className="text-sm font-semibold tracking-tight">RAG · Finances publiques</h1>
            <p className="text-[11px] text-muted-foreground">
              Assemblée Nationale · Sénat · Ministères
            </p>
          </div>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-5 space-y-4">
        {messages.length === 0 && (
          <div className="flex h-full flex-col items-center justify-center gap-6 py-10">
            <div className="text-center space-y-1">
              <p className="text-sm font-medium text-foreground/80">
                Interrogez les documents publics français
              </p>
              <p className="text-xs text-muted-foreground">
                53 documents · 4 464 extraits indexés
              </p>
            </div>
            <div className="flex flex-col gap-2 w-full max-w-sm">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => {
                    lastQuestion.current = s
                    onSend(s)
                  }}
                  className="rounded-xl border border-black/8 bg-white/60 px-4 py-2.5 text-left text-xs text-foreground/70 transition-colors hover:bg-white hover:text-foreground hover:shadow-sm dark:border-white/8 dark:bg-white/5 dark:hover:bg-white/10"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={cn("flex items-end gap-2", msg.role === "user" ? "justify-end" : "justify-start")}
          >
            {msg.role === "assistant" && (
              <span className="mb-0.5 flex size-5 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-orange-400 to-violet-500 text-[9px] font-bold text-white">
                R
              </span>
            )}
            <div
              className={cn(
                "max-w-[82%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
                msg.role === "user"
                  ? "rounded-br-sm bg-slate-900 text-white dark:bg-slate-700"
                  : "rounded-bl-sm bg-black/5 text-foreground dark:bg-white/8",
              )}
            >
              {msg.role === "assistant" ? (
                <>
                  {parseContent(msg.content, msg.citations, (c) =>
                    onCitationClick(c, lastQuestion.current),
                  )}
                  {isStreaming && i === messages.length - 1 && (
                    <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-current opacity-60" />
                  )}
                </>
              ) : (
                msg.content
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      <form
        onSubmit={handleSubmit}
        className="border-t border-black/5 p-4 dark:border-white/5"
      >
        <div className="flex items-center gap-2 rounded-xl border border-black/8 bg-white/70 px-3 py-2 shadow-sm transition-shadow focus-within:shadow-md focus-within:ring-2 focus-within:ring-violet-400/30 dark:border-white/8 dark:bg-white/5">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={isStreaming}
            placeholder="Posez votre question…"
            className="flex-1 bg-transparent text-sm outline-none placeholder:text-muted-foreground/60 disabled:opacity-50"
          />
          <Button
            type="submit"
            size="icon-sm"
            disabled={isStreaming || !input.trim()}
            className="shrink-0 rounded-lg bg-slate-900 text-white hover:bg-slate-800 dark:bg-white dark:text-slate-900 dark:hover:bg-slate-100"
          >
            {isStreaming ? (
              <span className="size-3 animate-spin rounded-full border-2 border-white border-t-transparent dark:border-slate-900 dark:border-t-transparent" />
            ) : (
              <svg
                viewBox="0 0 16 16"
                fill="none"
                className="size-3.5"
                stroke="currentColor"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M8 13V3M3 8l5-5 5 5" />
              </svg>
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
