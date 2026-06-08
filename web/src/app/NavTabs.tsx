"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import { clsx } from "clsx"

const TABS = [
  { href: "/", label: "Home", description: "What FairGuard is and where to start" },
  { href: "/findings", label: "Findings", description: "Former officials lobbying their old agency" },
  { href: "/search", label: "Search", description: "Look up a lobbyist, firm, client, agency, or legislator by name" },
  { href: "/trails", label: "Money trails", description: "USAspending awards to those clients" },
  { href: "/pressrel", label: "Press releases", description: "Congressional press releases mentioning the clients" },
  { href: "/graph", label: "Graph", description: "Conflict-of-interest network: composes scan + trace + pressrel" },
  { href: "/comments", label: "Comments", description: "Request-for-comment outreach status" },
  { href: "/methods", label: "Methods", description: "How the pipeline works and what it can / can't claim" },
  { href: "/glossary", label: "Glossary", description: "Plain-English definitions: LDA, §207, ALI, discretionary, …" },
]

export default function NavTabs() {
  const pathname = usePathname()
  return (
    <nav className="border-t border-slate-100 bg-white print:hidden">
      <div className="mx-auto flex max-w-6xl flex-wrap gap-1 px-6" role="tablist">
        {TABS.map((t) => {
          // /findings/[id] should still highlight the Findings tab.
          const active =
            pathname === t.href ||
            (t.href !== "/" && pathname.startsWith(t.href + "/"))
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
