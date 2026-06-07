import rawData from "../../../public/coi_graph.json"
import GraphClient from "./GraphClient"
import type { CoiGraphPayload } from "../types"

export default function GraphPage() {
  const data = rawData as CoiGraphPayload

  return (
    <div>
      <section className="mb-8">
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <span className="rounded-full bg-indigo-100 px-3 py-1 text-sm font-semibold text-indigo-800 ring-1 ring-indigo-200">
            Conflict-of-interest graph
          </span>
          <a
            href="/"
            className="text-sm font-semibold text-indigo-600 underline decoration-dotted hover:text-indigo-800"
          >
            ← Back to findings
          </a>
        </div>
        <h1 className="mb-4">Conflict-of-interest network</h1>
        <p className="max-w-3xl text-lg leading-relaxed text-slate-700">
          A composition of every other skill&apos;s output: the lobbyist → firm →
          agency chain (scan), the agency → client funding chain (trace), and the
          legislator → client public messaging chain (pressrel). The graph below
          surfaces three story shapes — <strong>triangles</strong>, <strong>hubs</strong>,
          and <strong>bridges</strong> — that aren&apos;t visible in any single
          skill&apos;s output.
        </p>

        {data && (
          <div className="mt-6 flex flex-wrap items-center gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4 text-base text-slate-700">
            <span className="font-semibold text-slate-900">
              {data.stats.n_nodes} nodes · {data.stats.n_edges} edges
            </span>
            <span className="text-slate-400">·</span>
            <span>
              {data.stats.nodes_by_type.lobbyist || 0} lobbyists ·
              {" "}{data.stats.nodes_by_type.firm || 0} firms ·
              {" "}{data.stats.nodes_by_type.agency || 0} agencies ·
              {" "}{data.stats.nodes_by_type.client || 0} clients ·
              {" "}{data.stats.nodes_by_type.legislator || 0} legislators
            </span>
            <span className="text-slate-400">·</span>
            <span>
              <strong className="text-rose-700">{data.triangles?.length || 0}</strong>{" "}
              triangle(s),{" "}
              <strong className="text-emerald-700">{data.hubs?.length || 0}</strong>{" "}
              hub(s),{" "}
              <strong className="text-indigo-700">{data.bridges?.length || 0}</strong>{" "}
              bridge(s)
            </span>
          </div>
        )}
      </section>

      {!data ? (
        <div className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-16 text-center">
          <p className="mb-3 text-xl font-semibold text-slate-600">No graph data yet</p>
          <p className="text-base text-slate-500">
            Run{" "}
            <code className="rounded bg-slate-100 px-2 py-1 font-mono text-sm">
              uv run scripts/06_coi_graph.py
            </code>{" "}
            to generate <code className="font-mono text-sm">web/public/coi_graph.json</code>.
          </p>
        </div>
      ) : (
        <GraphClient initialData={data} />
      )}

      <aside className="mt-12 rounded-xl border border-amber-200 bg-amber-50 p-6">
        <p className="mb-2 text-base font-bold text-amber-900">Editorial note</p>
        <p className="text-base leading-relaxed text-amber-900">
          A triangle is a <em>lead</em>, not a story. Before publishing:
          confirm the legislator&apos;s committee jurisdiction covers the
          agency, check the §207 cooling-off status of the lobbyist
          (<code className="font-mono text-sm">notes/09</code>), and document
          a real request for comment
          (<code className="font-mono text-sm">notes/comment_requests/</code>).
          The graph surfaces structure. The story is built from the structure.
        </p>
      </aside>
    </div>
  )
}
