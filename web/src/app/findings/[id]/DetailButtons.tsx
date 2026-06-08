"use client"

import { useState } from "react"
import { clsx } from "clsx"
import { copyToClipboard, downloadBlob } from "../../lib/exports"

const BTN =
  "inline-flex items-center gap-1 rounded-lg border border-slate-300 bg-white px-3 py-1.5 text-sm font-semibold text-slate-700 transition hover:border-indigo-300 hover:bg-indigo-50 hover:text-indigo-700"

export function CopyButton({ text, label }: { text: string; label: string }) {
  const [done, setDone] = useState(false)
  const onClick = async () => {
    const ok = await copyToClipboard(text)
    if (ok) {
      setDone(true)
      setTimeout(() => setDone(false), 1200)
    }
  }
  return (
    <button type="button" onClick={onClick} className={clsx(BTN, done && "border-emerald-400 bg-emerald-50 text-emerald-700")}>
      {done ? "Copied ✓" : label}
    </button>
  )
}

export function DownloadButton({
  content, filename, mime, label,
}: { content: string; filename: string; mime: string; label: string }) {
  return (
    <button
      type="button"
      onClick={() => downloadBlob(content, filename, mime)}
      className={BTN}
    >
      {label}
    </button>
  )
}
