"use client"

import { useState } from "react"
import { ChatPanel } from "@/components/chat-panel"
import { SourcePanel } from "@/components/source-panel"
import { type Citation, useChat } from "@/hooks/use-chat"
import { cn } from "@/lib/utils"

export default function Home() {
  const { messages, isStreaming, sendMessage } = useChat()
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null)
  const [activeQuery, setActiveQuery] = useState("")

  function handleCitationClick(citation: Citation, question: string) {
    setActiveCitation(citation)
    setActiveQuery(question)
  }

  const showSource = activeCitation !== null

  return (
    <div className="relative flex h-[100dvh] overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-br from-orange-100 via-pink-50 to-violet-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950"
      />

      <div className="flex w-full flex-col gap-3 p-3 md:flex-row">
        {/* Chat panel — full width on mobile, half on md+ */}
        <div
          className={cn(
            "flex flex-col overflow-hidden rounded-2xl bg-white/85 shadow-xl ring-1 ring-black/5 backdrop-blur-md transition-all dark:bg-slate-900/85 dark:ring-white/5",
            showSource ? "hidden md:flex md:w-1/2" : "flex w-full md:w-1/2",
          )}
        >
          <ChatPanel
            messages={messages}
            isStreaming={isStreaming}
            onSend={sendMessage}
            onCitationClick={handleCitationClick}
          />
        </div>

        {/* Source panel — hidden on mobile until a citation is clicked */}
        <div
          className={cn(
            "flex flex-col overflow-hidden rounded-2xl bg-white/85 shadow-xl ring-1 ring-black/5 backdrop-blur-md transition-all dark:bg-slate-900/85 dark:ring-white/5",
            showSource ? "flex w-full md:w-1/2" : "hidden md:flex md:w-1/2",
          )}
        >
          {/* Mobile back button */}
          {showSource && (
            <button
              onClick={() => setActiveCitation(null)}
              className="flex items-center gap-1.5 border-b border-black/5 px-4 py-2 text-xs text-muted-foreground hover:text-foreground md:hidden dark:border-white/5"
            >
              ← Retour au chat
            </button>
          )}
          <SourcePanel citation={activeCitation} query={activeQuery} />
        </div>
      </div>
    </div>
  )
}
