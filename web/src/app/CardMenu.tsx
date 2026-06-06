"use client"

import { useEffect, useRef, useState } from "react"
import { clsx } from "clsx"

export type MenuItem =
  | { type: "action"; label: string; hint?: string; onClick: () => void | Promise<void>; danger?: boolean }
  | { type: "link"; label: string; hint?: string; href: string; external?: boolean }
  | { type: "divider" }

/**
 * Three-dot (kebab) menu. Opens on click, closes on outside click / Escape /
 * action. Large hit area for older or non-technical reporters: 44×44 trigger,
 * generous 48px-tall menu rows, descriptive subtitles per row.
 */
export default function CardMenu({
  items,
  label = "More actions",
}: {
  items: MenuItem[]
  label?: string
}) {
  const [open, setOpen] = useState(false)
  const [toast, setToast] = useState<string | null>(null)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    const onClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") setOpen(false)
    }
    document.addEventListener("mousedown", onClick)
    document.addEventListener("keydown", onKey)
    return () => {
      document.removeEventListener("mousedown", onClick)
      document.removeEventListener("keydown", onKey)
    }
  }, [open])

  useEffect(() => {
    if (!toast) return
    const t = setTimeout(() => setToast(null), 2200)
    return () => clearTimeout(t)
  }, [toast])

  const run = async (it: Extract<MenuItem, { type: "action" }>) => {
    setOpen(false)
    const maybe = it.onClick()
    if (maybe instanceof Promise) {
      try {
        await maybe
        setToast(`✓ ${it.label}`)
      } catch (e) {
        setToast(`Failed: ${e instanceof Error ? e.message : String(e)}`)
      }
    } else {
      setToast(`✓ ${it.label}`)
    }
  }

  return (
    <div className="relative" ref={ref}>
      <button
        type="button"
        aria-label={label}
        aria-haspopup="menu"
        aria-expanded={open}
        onClick={() => setOpen((v) => !v)}
        className={clsx(
          "inline-flex h-11 w-11 items-center justify-center rounded-full text-2xl leading-none transition",
          open
            ? "bg-indigo-600 text-white"
            : "bg-slate-100 text-slate-600 hover:bg-slate-200 hover:text-slate-900"
        )}
        title={label}
      >
        <span aria-hidden>⋯</span>
      </button>

      {open && (
        <div
          role="menu"
          className="absolute right-0 z-20 mt-2 w-72 overflow-hidden rounded-xl border border-slate-200 bg-white shadow-xl"
        >
          {items.map((it, i) => {
            if (it.type === "divider") {
              return <div key={`d-${i}`} className="my-1 h-px bg-slate-100" aria-hidden />
            }
            if (it.type === "link") {
              return (
                <a
                  key={`l-${i}`}
                  href={it.href}
                  target={it.external ? "_blank" : undefined}
                  rel={it.external ? "noopener noreferrer" : undefined}
                  onClick={() => setOpen(false)}
                  role="menuitem"
                  className="block px-4 py-3 text-left text-base text-slate-800 hover:bg-indigo-50 hover:text-indigo-900"
                >
                  <div className="font-semibold">{it.label}</div>
                  {it.hint && <div className="text-sm text-slate-500">{it.hint}</div>}
                </a>
              )
            }
            return (
              <button
                key={`a-${i}`}
                type="button"
                role="menuitem"
                onClick={() => run(it)}
                className={clsx(
                  "block w-full px-4 py-3 text-left text-base transition",
                  it.danger
                    ? "text-rose-700 hover:bg-rose-50"
                    : "text-slate-800 hover:bg-indigo-50 hover:text-indigo-900"
                )}
              >
                <div className="font-semibold">{it.label}</div>
                {it.hint && <div className="text-sm text-slate-500">{it.hint}</div>}
              </button>
            )
          })}
        </div>
      )}

      {toast && (
        <div
          role="status"
          aria-live="polite"
          className="absolute right-0 top-12 z-30 whitespace-nowrap rounded-lg bg-slate-900 px-3 py-2 text-sm font-medium text-white shadow-lg"
        >
          {toast}
        </div>
      )}
    </div>
  )
}
