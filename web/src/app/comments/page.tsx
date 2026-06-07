import rawData from "../../../public/comment_log.json"
import CommentsClient from "./CommentsClient"
import type { CommentLogPayload } from "../types"

export default function CommentsPage() {
  const data = rawData as CommentLogPayload

  const urgent = data.entries.filter((e) =>
    ["escalated_to_counsel", "no_response_by_deadline"].includes(e.status)
  ).length
  const active = data.entries.filter((e) =>
    ["sent", "acknowledged", "awaiting_substantive"].includes(e.status)
  ).length
  const replied = data.entries.filter((e) =>
    ["responded", "closed_response"].includes(e.status)
  ).length

  return (
    <div>
      <section className="mb-10">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-sm font-semibold text-emerald-800 ring-1 ring-emerald-200">
            Request-for-comment workflow
          </span>
          <a
            href="/"
            className="text-sm font-semibold text-indigo-600 underline decoration-dotted hover:text-indigo-800"
          >
            ← Back to findings
          </a>
        </div>
        <h1 className="mb-4">Comment outreach status</h1>
        <p className="max-w-3xl text-lg leading-relaxed text-slate-700">
          Tracks every request for comment sent to a firm named in the structural
          finding. Status is derived from the event timeline (sent →
          acknowledged → substantive reply → closed), with deadline pressure
          flagging overdue outreach in red. Editorial gate before any of the
          named findings goes to print.
        </p>
        <div className="mt-6 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 text-base text-slate-700">
          <span className="font-semibold text-slate-900">To log an event:</span>
          <code className="rounded-md bg-emerald-50 px-2 py-1 font-mono text-sm text-emerald-700 ring-1 ring-emerald-100">
            /fair-guard comment
          </code>
          <span className="text-slate-400">or directly:</span>
          <code className="rounded-md bg-slate-100 px-2 py-1 font-mono text-sm text-slate-700">
            uv run scripts/07_comment_tracker.py log &lt;firm&gt; sent --addresses …
          </code>
        </div>

        {/* Summary chip strip */}
        <div className="mt-4 flex flex-wrap items-center gap-3 text-base">
          {urgent > 0 && (
            <span className="rounded-full bg-rose-100 px-3 py-1 font-semibold text-rose-800 ring-1 ring-rose-300">
              ⚠ {urgent} urgent
            </span>
          )}
          {active > 0 && (
            <span className="rounded-full bg-amber-100 px-3 py-1 font-semibold text-amber-800 ring-1 ring-amber-300">
              ⏳ {active} active
            </span>
          )}
          {replied > 0 && (
            <span className="rounded-full bg-emerald-100 px-3 py-1 font-semibold text-emerald-800 ring-1 ring-emerald-300">
              ✓ {replied} replied
            </span>
          )}
          <span className="rounded-full bg-slate-100 px-3 py-1 font-semibold text-slate-700 ring-1 ring-slate-300">
            {data.n_entries} total firms
          </span>
        </div>
      </section>

      <CommentsClient initialData={data} />

      <aside className="mt-12 rounded-xl border border-amber-200 bg-amber-50 p-6">
        <p className="mb-2 text-base font-bold text-amber-900">Editorial note</p>
        <p className="text-base leading-relaxed text-amber-900">
          A documented request for comment is a publication gate, not a courtesy.
          The drafts in <code className="font-mono text-sm">notes/comment_requests/</code> are
          ready to send; the source-of-truth log in{" "}
          <code className="font-mono text-sm">notes/comment_requests/comment_log.json</code>{" "}
          is committed so a fact-checker can audit the outreach record. Use{" "}
          <code className="font-mono text-sm">--pointer</code>, not bodies — never
          paste private email contents into the log. Legal threats escalate
          everything: stop, hand off to counsel, do not log further events
          without their guidance.
        </p>
      </aside>
    </div>
  )
}
