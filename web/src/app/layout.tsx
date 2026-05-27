import type { Metadata } from "next"
import "./globals.css"

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
        <header className="border-b border-slate-200 bg-white px-6 py-4">
          <div className="mx-auto max-w-5xl flex items-center justify-between">
            <div>
              <span className="text-lg font-bold text-slate-900">FairGuard</span>
              <span className="ml-2 text-sm text-slate-500">
                Revolving Door Verification UI
              </span>
            </div>
            <span className="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-800">
              Competition draft — not for publication
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-8">{children}</main>
        <footer className="border-t border-slate-200 bg-white px-6 py-4 text-center text-xs text-slate-400">
          FairGuard · Northwestern GAIN Agentic AI Investigative Journalism Challenge · July 2026 ·{" "}
          <a
            href="https://github.com/fairguard/northwestern-challenge"
            className="underline hover:text-slate-600"
          >
            Source
          </a>
        </footer>
      </body>
    </html>
  )
}
