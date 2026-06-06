"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { clsx } from "clsx"

const TABS = [
  { href: "/", label: "Findings", description: "Former officials lobbying their old agency" },
  { href: "/trails", label: "Money trails", description: "USAspending awards to those clients" },
]

export default function NavTabs() {
  const pathname = usePathname()
  return (
    <nav className="border-t border-slate-100 bg-white">
      <div className="mx-auto flex max-w-6xl gap-1 px-6" role="tablist">
        {TABS.map((t) => {
          const active = pathname === t.href
          return (
            <Link
              key={t.href}
              href={t.href}
              role="tab"
              aria-selected={active}
              className={clsx(
                "border-b-2 px-4 py-3 text-base font-semibold transition",
                active
                  ? "border-indigo-600 text-indigo-700"
                  : "border-transparent text-slate-500 hover:border-slate-300 hover:text-slate-800"
              )}
              title={t.description}
            >
              {t.label}
            </Link>
          )
        })}
      </div>
    </nav>
  )
}
