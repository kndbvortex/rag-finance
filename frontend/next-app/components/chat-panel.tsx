"use client"

import { useEffect, useRef, useState } from "react"
import { HugeiconsIcon } from "@hugeicons/react"
import {
  ArrowUp02Icon,
  ArrowReloadHorizontalIcon,
  Building04Icon,
  Copy01Icon,
} from "@hugeicons/core-free-icons"
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar"
import { Bubble, BubbleContent } from "@/components/ui/bubble"
import { Button } from "@/components/ui/button"
import {
  Message,
  MessageAvatar,
  MessageContent,
  MessageFooter,
} from "@/components/ui/message"
import {
  MessageScroller,
  MessageScrollerButton,
  MessageScrollerContent,
  MessageScrollerItem,
  MessageScrollerProvider,
  MessageScrollerViewport,
} from "@/components/ui/message-scroller"
import { type Citation, type Message as Msg } from "@/hooks/use-chat"
import { cn } from "@/lib/utils"

const AI_AVATAR = "/llama.webp"
const USER_AVATAR = "https://v3.shadcn.com/avatars/02.png"

interface Props {
  messages: Msg[]
  isStreaming: boolean
  onSend: (question: string) => void
  onCitationClick: (citation: Citation, question: string) => void
}

const SUGGESTIONS = [
  "Quel était le déficit public français en 2018 ?",
  "Quelle est la trajectoire des prélèvements obligatoires par rapport au PIB ?",
  "Qu'est-ce que la dotation instituée au profit des communes au 1er janvier 2024 ?",
]

function parseContent(
  content: string,
  citations: Citation[],
  onCitationClick: (c: Citation) => void
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
            <span className="text-[10px] leading-none">↗</span>
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

export function ChatPanel({
  messages,
  isStreaming,
  onSend,
  onCitationClick,
}: Props) {
  const [input, setInput] = useState("")
  const lastQuestion = useRef("")
  const [stats, setStats] = useState<{
    documents: number
    chunks: number
  } | null>(null)

  useEffect(() => {
    fetch("http://localhost:8000/api/v1/stats")
      .then((r) => r.json())
      .then(setStats)
      .catch(() => null)
  }, [])

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
      {/* Header */}
      <div className="border-b border-black/5 px-5 py-3.5 dark:border-white/5">
        <div className="flex items-center gap-3">
          <img
            src="/logo.jpg"
            alt="Logo"
            className="h-9 w-auto rounded-lg object-contain"
          />
          <div>
            <h1 className="text-sm font-semibold tracking-tight">
              Finances publiques françaises
            </h1>
            <p className="text-[11px] text-muted-foreground">
              Impôts · Fiscalité · Documents officiels
            </p>
          </div>
        </div>
      </div>

      {/* Message list */}
      <MessageScrollerProvider autoScroll scrollPreviousItemPeek={80}>
        <MessageScroller className="flex-1">
          <MessageScrollerViewport className="px-5 py-4">
            <MessageScrollerContent>
              {messages.length === 0 && (
                <div className="flex h-full min-h-[300px] flex-col items-center justify-center gap-5">
                  <div className="flex size-12 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-100 to-violet-100 dark:from-slate-800 dark:to-slate-700">
                    <HugeiconsIcon
                      icon={Building04Icon}
                      size={22}
                      className="text-violet-500"
                      strokeWidth={1.5}
                    />
                  </div>
                  <div className="space-y-1 text-center">
                    <p className="text-sm font-medium">
                      Documents publics français
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {stats
                        ? `${stats.documents} documents · ${stats.chunks.toLocaleString("fr-FR")} extraits indexés`
                        : "Chargement…"}
                    </p>
                  </div>
                  <div className="flex w-full max-w-sm flex-col gap-2">
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

              {messages.map((msg, i) => {
                const isLastAssistant =
                  msg.role === "assistant" && i === messages.length - 1
                const isThinking =
                  isLastAssistant && isStreaming && msg.content === ""

                return (
                  <MessageScrollerItem
                    key={i}
                    messageId={String(i)}
                    scrollAnchor={msg.role === "user"}
                  >
                    <Message align={msg.role === "user" ? "end" : "start"}>
                      <MessageAvatar>
                        <Avatar className="size-8 rounded-lg">
                          <AvatarImage
                            src={
                              msg.role === "assistant" ? AI_AVATAR : USER_AVATAR
                            }
                            alt={msg.role === "assistant" ? "AI" : "Vous"}
                          />
                          <AvatarFallback className="rounded-lg text-xs">
                            {msg.role === "assistant" ? "AI" : "U"}
                          </AvatarFallback>
                        </Avatar>
                      </MessageAvatar>

                      <MessageContent>
                        <Bubble
                          variant={msg.role === "user" ? "default" : "ghost"}
                          align={msg.role === "user" ? "end" : "start"}
                        >
                          <BubbleContent
                            className={cn(
                              msg.role === "user"
                                ? "bg-slate-900 text-white dark:bg-slate-700"
                                : msg.isError
                                  ? "text-destructive"
                                  : "text-foreground"
                            )}
                          >
                            {msg.role === "assistant" ? (
                              isThinking ? (
                                <span className="shimmer text-muted-foreground shimmer-duration-1500">
                                  Génération en cours…
                                </span>
                              ) : msg.isError ? (
                                <span className="flex items-center gap-2">
                                  <span>⚠</span>
                                  {msg.content}
                                </span>
                              ) : (
                                <>
                                  {parseContent(
                                    msg.content,
                                    msg.citations,
                                    (c) =>
                                      onCitationClick(c, lastQuestion.current)
                                  )}
                                  {isStreaming && isLastAssistant && (
                                    <span className="ml-0.5 inline-block h-3.5 w-0.5 animate-pulse bg-current opacity-60" />
                                  )}
                                </>
                              )
                            ) : (
                              msg.content
                            )}
                          </BubbleContent>
                        </Bubble>
                        {msg.isError && (
                          <MessageFooter>
                            <button
                              onClick={() => onSend(lastQuestion.current)}
                              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-black/5 hover:text-foreground dark:hover:bg-white/8"
                              aria-label="Réessayer"
                            >
                              <HugeiconsIcon
                                icon={ArrowReloadHorizontalIcon}
                                size={12}
                                strokeWidth={2}
                              />
                              Réessayer
                            </button>
                            <button
                              onClick={() =>
                                navigator.clipboard.writeText(
                                  lastQuestion.current
                                )
                              }
                              className="flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-muted-foreground transition-colors hover:bg-black/5 hover:text-foreground dark:hover:bg-white/8"
                              aria-label="Copier la question"
                            >
                              <HugeiconsIcon
                                icon={Copy01Icon}
                                size={12}
                                strokeWidth={2}
                              />
                              Copier
                            </button>
                          </MessageFooter>
                        )}
                      </MessageContent>
                    </Message>
                  </MessageScrollerItem>
                )
              })}
            </MessageScrollerContent>
          </MessageScrollerViewport>
          <MessageScrollerButton />
        </MessageScroller>
      </MessageScrollerProvider>

      {/* Input */}
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
              <HugeiconsIcon icon={ArrowUp02Icon} size={14} strokeWidth={2.5} />
            )}
          </Button>
        </div>
      </form>
    </div>
  )
}
