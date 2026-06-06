import type { Metadata } from "next"
import Link from "next/link"
import "./globals.css"
import NavTabs from "./NavTabs"

export const metadata: Metadata = {
  title: "FairGuard — Revolving Door Findings",
  description:
    "Reporter-facing verification interface for FairGuard investigative findings. " +
    "Each claim links to the specific LDA filing record that supports it.",
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body>
        <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur">
          <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-4">
            <Link href="/" className="flex items-baseline gap-3">
              <span className="text-2xl font-bold tracking-tight text-slate-900">
                FairGuard
              </span>
              <span className="hidden text-base text-slate-500 sm:inline">
                Revolving Door Verification
              </span>
            </Link>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-sm font-medium text-amber-800 ring-1 ring-amber-200">
              Competition draft — not for publication
            </span>
          </div>
          <NavTabs />
        </header>
        <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
        <footer className="border-t border-slate-200 bg-white px-6 py-6 text-center text-sm text-slate-500">
          FairGuard · Northwestern GAIN Agentic AI Investigative Journalism Challenge · July 2026 ·{" "}
          <a
            href="https://github.com/fairguard/northwestern-challenge"
            className="font-medium text-indigo-600 underline decoration-dotted hover:text-indigo-800"
          >
            Source
          </a>
        </footer>
      </body>
    </html>
  )
}
