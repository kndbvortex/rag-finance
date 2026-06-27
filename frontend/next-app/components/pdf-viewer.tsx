"use client"

interface Props {
  pdfUrl: string
  pageStart: number
}

export function PdfViewer({ pdfUrl, pageStart }: Props) {
  const src = `${pdfUrl}#page=${pageStart}`

  return (
    <iframe
      src={src}
      className="h-full w-full"
      title="Document source"
    />
  )
}
