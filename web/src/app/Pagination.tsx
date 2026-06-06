"use client"

import { clsx } from "clsx"

/**
 * Numbered pager with prev/next. Designed for large click targets and clear
 * "where am I" feedback — older or non-technical reporters can scan and click
 * without keyboard tricks. Hidden entirely when there's only one page.
 */
export default function Pagination({
  page,
  pageCount,
  total,
  pageSize,
  onPage,
  itemLabel = "results",
}: {
  page: number
  pageCount: number
  total: number
  pageSize: number
  onPage: (p: number) => void
  itemLabel?: string
}) {
  if (pageCount <= 1) {
    return (
      <p className="mt-6 text-center text-base text-slate-500">
        Showing all <strong className="text-slate-700">{total}</strong> {itemLabel}.
      </p>
    )
  }

  const start = (page - 1) * pageSize + 1
  const end = Math.min(page * pageSize, total)

  // Window of page numbers around the current page, with boundary anchors.
  const windowed = (): (number | "…")[] => {
    const pages = new Set<number>([1, pageCount, page - 1, page, page + 1])
    const valid = [...pages].filter((p) => p >= 1 && p <= pageCount).sort((a, b) => a - b)
    const out: (number | "…")[] = []
    let prev = 0
    for (const p of valid) {
      if (prev && p - prev > 1) out.push("…")
      out.push(p)
      prev = p
    }
    return out
  }

  const PageBtn = ({
    children,
    onClick,
    active,
    disabled,
    label,
  }: {
    children: React.ReactNode
    onClick: () => void
    active?: boolean
    disabled?: boolean
    label?: string
  }) => (
    <button
      onClick={onClick}
      disabled={disabled}
      aria-label={label}
      aria-current={active ? "page" : undefined}
      className={clsx(
        "inline-flex h-11 min-w-[2.75rem] items-center justify-center rounded-lg border px-3 text-base font-semibold transition",
        active
          ? "border-indigo-600 bg-indigo-600 text-white"
          : disabled
            ? "border-slate-200 bg-slate-50 text-slate-300"
            : "border-slate-300 bg-white text-slate-700 hover:border-indigo-400 hover:text-indigo-700"
      )}
    >
      {children}
    </button>
  )

  return (
    <div className="mt-8 flex flex-col items-center gap-3">
      <p className="text-base text-slate-600">
        Showing <strong className="text-slate-900">{start}–{end}</strong> of{" "}
        <strong className="text-slate-900">{total}</strong> {itemLabel}
      </p>
      <div className="flex flex-wrap items-center justify-center gap-2">
        <PageBtn onClick={() => onPage(page - 1)} disabled={page === 1} label="Previous page">
          ← Prev
        </PageBtn>
        {windowed().map((p, i) =>
          p === "…" ? (
            <span key={`gap-${i}`} className="px-2 text-base text-slate-400">
              …
            </span>
          ) : (
            <PageBtn
              key={p}
              onClick={() => onPage(p)}
              active={p === page}
              label={`Go to page ${p}`}
            >
              {p}
            </PageBtn>
          )
        )}
        <PageBtn onClick={() => onPage(page + 1)} disabled={page === pageCount} label="Next page">
          Next →
        </PageBtn>
      </div>
    </div>
  )
}
