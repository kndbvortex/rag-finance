"use client"

import { useState } from "react"
import { ChatPanel } from "@/components/chat-panel"
import { SourcePanel } from "@/components/source-panel"
import { type Citation, useChat } from "@/hooks/use-chat"

export default function Home() {
  const { messages, isStreaming, sendMessage } = useChat()
  const [activeCitation, setActiveCitation] = useState<Citation | null>(null)
  const [activeQuery, setActiveQuery] = useState("")

  function handleCitationClick(citation: Citation, question: string) {
    setActiveCitation(citation)
    setActiveQuery(question)
  }

  return (
    <div className="relative flex h-screen overflow-hidden">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 -z-10 bg-gradient-to-br from-orange-100 via-pink-50 to-violet-100 dark:from-slate-950 dark:via-slate-900 dark:to-slate-950"
      />
      <div className="flex w-full gap-3 p-3">
        <div className="flex w-1/2 flex-col overflow-hidden rounded-2xl bg-white/85 shadow-xl ring-1 ring-black/5 backdrop-blur-md dark:bg-slate-900/85 dark:ring-white/5">
          <ChatPanel
            messages={messages}
            isStreaming={isStreaming}
            onSend={sendMessage}
            onCitationClick={handleCitationClick}
          />
        </div>
        <div className="flex w-1/2 flex-col overflow-hidden rounded-2xl bg-white/85 shadow-xl ring-1 ring-black/5 backdrop-blur-md dark:bg-slate-900/85 dark:ring-white/5">
          <SourcePanel citation={activeCitation} query={activeQuery} />
        </div>
      </div>
    </div>
  )
}
