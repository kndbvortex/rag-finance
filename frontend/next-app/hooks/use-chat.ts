"use client"

import { useCallback, useState } from "react"

export interface Citation {
  index: number
  institution: string
  type_document: string
  annee_fiscale: number | null
  url: string
  contient_tableaux: boolean
  content: string
}

export interface Message {
  role: "user" | "assistant"
  content: string
  citations: Citation[]
}

export function useChat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [isStreaming, setIsStreaming] = useState(false)

  const sendMessage = useCallback(
    async (question: string) => {
      if (isStreaming) return

      setMessages((prev) => [
        ...prev,
        { role: "user", content: question, citations: [] },
        { role: "assistant", content: "", citations: [] },
      ])
      setIsStreaming(true)

      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/api/v1/chat/stream`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ question }),
          },
        )

        const reader = response.body!.getReader()
        const decoder = new TextDecoder()
        let buffer = ""

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() ?? ""

          for (const line of lines) {
            if (!line.startsWith("data: ")) continue
            const data = JSON.parse(line.slice(6))

            if (data.type === "token") {
              setMessages((prev) => {
                const updated = [...prev]
                const last = { ...updated[updated.length - 1] }
                last.content += data.content
                updated[updated.length - 1] = last
                return updated
              })
            } else if (data.type === "done") {
              setMessages((prev) => {
                const updated = [...prev]
                const last = { ...updated[updated.length - 1] }
                last.citations = data.sources ?? []
                updated[updated.length - 1] = last
                return updated
              })
            }
          }
        }
      } finally {
        setIsStreaming(false)
      }
    },
    [isStreaming],
  )

  return { messages, isStreaming, sendMessage }
}
