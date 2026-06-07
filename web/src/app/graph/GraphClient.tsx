"use client"

import { useEffect, useMemo, useRef, useState } from "react"
import { clsx } from "clsx"
import { forceCenter, forceLink, forceManyBody, forceSimulation, type SimulationNodeDatum } from "d3-force"
import { select } from "d3-selection"
import { drag } from "d3-drag"
import { zoom, zoomIdentity } from "d3-zoom"
import type { CoiGraphPayload, CoiLink, CoiNode, CoiTriangle } from "../types"

// ── Constants ──────────────────────────────────────────────────────────────────

const NODE_TYPES = ["lobbyist", "firm", "agency", "client", "legislator"] as const
type NodeType = (typeof NODE_TYPES)[number]

const TYPE_LABELS: Record<NodeType, string> = {
  lobbyist: "Lobbyists",
  firm: "Firms",
  agency: "Agencies",
  client: "Clients",
  legislator: "Legislators",
}

const fmtUSD = (n: number) =>
  n >= 1_000_000_000
    ? `$${(n / 1_000_000_000).toFixed(2)}B`
    : n >= 1_000_000
      ? `$${(n / 1_000_000).toFixed(1)}M`
      : `$${n.toLocaleString()}`

// ── Force-directed canvas (D3 simulation, SVG render) ──────────────────────────

type SimNode = CoiNode & SimulationNodeDatum
type SimLink = Omit<CoiLink, "source" | "target"> & { source: SimNode; target: SimNode }

function ForceGraph({
  data,
  visibleTypes,
  onNodeClick,
  selectedNodeId,
}: {
  data: CoiGraphPayload
  visibleTypes: Set<NodeType>
  onNodeClick: (n: CoiNode | null) => void
  selectedNodeId: string | null
}) {
  const ref = useRef<SVGSVGElement>(null)
  const width = 1100
  const height = 700

  useEffect(() => {
    if (!ref.current) return
    const svg = select(ref.current)
    svg.selectAll("*").remove()

    const visibleNodeIds = new Set(
      data.nodes
        .filter((n) => visibleTypes.has(n.type as NodeType))
        .map((n) => n.id)
    )
    const nodes: SimNode[] = data.nodes
      .filter((n) => visibleNodeIds.has(n.id))
      .map((n) => ({ ...n }))

    const links: SimLink[] = data.links
      .filter((l) => {
        const s = typeof l.source === "string" ? l.source : l.source.id
        const t = typeof l.target === "string" ? l.target : l.target.id
        return visibleNodeIds.has(s) && visibleNodeIds.has(t)
      })
      .map((l) => ({ ...l })) as SimLink[]

    // Outer group for zoom/pan transforms.
    const container = svg.append("g").attr("class", "viewport")

    // Zoom + pan: scroll to zoom, drag (on background) to pan.
    const zoomBehavior = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4])
      .on("zoom", (event) => {
        container.attr("transform", event.transform.toString())
      })
    svg.call(zoomBehavior).on("dblclick.zoom", null)
    svg.call(zoomBehavior.transform, zoomIdentity)

    // Links
    const link = container
      .append("g")
      .attr("stroke-opacity", 0.45)
      .selectAll("line")
      .data(links)
      .join("line")
      .attr("stroke", (d) => d.color)
      .attr("stroke-width", (d) => Math.max(1, d.width || 1))
      .attr("stroke-dasharray", (d) => (d.dash ? d.dash : null))

    // Nodes
    const node = container
      .append("g")
      .selectAll<SVGCircleElement, SimNode>("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => d.radius || 6)
      .attr("fill", (d) => d.color)
      .attr("stroke", (d) => (d.id === selectedNodeId ? "#0f172a" : "white"))
      .attr("stroke-width", (d) => (d.id === selectedNodeId ? 3 : 1.5))
      .style("cursor", "pointer")
      .on("click", (_event, d) => onNodeClick(d))

    node.append("title").text((d) => `${d.label} (${d.type})`)

    // Labels for higher-degree types only — avoids label spaghetti.
    const labels = container
      .append("g")
      .attr("font-size", 11)
      .attr("font-weight", 600)
      .attr("text-anchor", "middle")
      .attr("fill", "#0f172a")
      .attr("pointer-events", "none")
      .selectAll<SVGTextElement, SimNode>("text")
      .data(nodes.filter((n) => ["lobbyist", "agency", "firm"].includes(n.type)))
      .join("text")
      .text((d) => d.label.slice(0, 36))

    // Drag behavior — pin nodes by holding the simulation in place after drop.
    const dragBehavior = drag<SVGCircleElement, SimNode>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart()
        d.fx = d.x
        d.fy = d.y
      })
      .on("drag", (event, d) => {
        d.fx = event.x
        d.fy = event.y
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0)
        // Leave d.fx / d.fy set so the node stays where dropped.
      })
    node.call(dragBehavior)

    const simulation = forceSimulation<SimNode>(nodes)
      .force("link", forceLink<SimNode, SimLink>(links).id((d) => d.id).distance(80).strength(0.4))
      .force("charge", forceManyBody().strength(-160))
      .force("center", forceCenter(width / 2, height / 2))
      .on("tick", () => {
        link
          .attr("x1", (d) => d.source.x!)
          .attr("y1", (d) => d.source.y!)
          .attr("x2", (d) => d.target.x!)
          .attr("y2", (d) => d.target.y!)
        node.attr("cx", (d) => d.x!).attr("cy", (d) => d.y!)
        labels.attr("x", (d) => d.x!).attr("y", (d) => (d.y ?? 0) + (d.radius || 6) + 12)
      })

    return () => {
      simulation.stop()
    }
  }, [data, visibleTypes, selectedNodeId, onNodeClick])

  return (
    <svg
      ref={ref}
      width="100%"
      viewBox={`0 0 ${width} ${height}`}
      className="block h-[700px] w-full rounded-xl border border-slate-200 bg-slate-50"
      role="img"
      aria-label="Conflict-of-interest force-directed graph"
    />
  )
}

// ── Side panels ────────────────────────────────────────────────────────────────

function TrianglesPanel({ triangles }: { triangles: CoiTriangle[] }) {
  if (!triangles?.length) return null
  return (
    <section className="mb-6 rounded-xl border border-rose-200 bg-rose-50 p-5">
      <h2 className="mb-3 text-2xl">Structural triangles ({triangles.length})</h2>
      <p className="mb-4 text-base text-slate-700">
        Each row is a member of Congress publicly mentioning a client whose lobbyist used to staff
        that client&apos;s funding agency. Order: mentions, then dollars.
      </p>
      <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
        <table className="w-full text-base">
          <thead className="bg-slate-50">
            <tr className="text-left text-sm uppercase tracking-wider text-slate-600">
              <th className="px-4 py-2 font-semibold">Legislator</th>
              <th className="px-4 py-2 font-semibold">Client</th>
              <th className="px-4 py-2 font-semibold">Agency</th>
              <th className="px-4 py-2 font-semibold">Lobbyist(s)</th>
              <th className="px-4 py-2 text-right font-semibold">Mentions</th>
              <th className="px-4 py-2 text-right font-semibold">Agency $</th>
            </tr>
          </thead>
          <tbody>
            {triangles.slice(0, 25).map((t, i) => (
              <tr key={`${t.legislator}-${t.client}-${t.agency}-${i}`} className="border-t border-slate-100">
                <td className="px-4 py-2 font-semibold text-slate-900">{t.legislator}</td>
                <td className="px-4 py-2 text-emerald-700">{t.client}</td>
                <td className="px-4 py-2 text-rose-700">{t.agency}</td>
                <td className="px-4 py-2 text-slate-700">{t.lobbyists.join(", ")}</td>
                <td className="px-4 py-2 text-right tabular-nums">{t.n_mentions}</td>
                <td className="px-4 py-2 text-right font-mono tabular-nums">
                  {t.agency_to_client_dollars ? fmtUSD(t.agency_to_client_dollars) : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  )
}

function NodeInspector({ node, links, nodes }: { node: CoiNode; links: CoiLink[]; nodes: CoiNode[] }) {
  const nodeById = useMemo(() => new Map(nodes.map((n) => [n.id, n])), [nodes])
  const incident = links.filter((l) => {
    const s = typeof l.source === "string" ? l.source : l.source.id
    const t = typeof l.target === "string" ? l.target : l.target.id
    return s === node.id || t === node.id
  })
  return (
    <aside className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="mb-3 flex items-baseline gap-3">
        <span
          className="rounded-full px-3 py-1 text-sm font-bold uppercase tracking-wide text-white"
          style={{ backgroundColor: node.color }}
        >
          {node.type}
        </span>
        <h2 className="text-2xl">{node.label}</h2>
      </div>
      {node.type === "lobbyist" && (
        <dl className="mb-4 grid grid-cols-2 gap-2 text-sm">
          {node.rank != null && (
            <><dt className="text-slate-500">Rank</dt><dd>#{node.rank}</dd></>
          )}
          {node.concentration != null && (
            <><dt className="text-slate-500">Concentration</dt><dd>{Math.round((node.concentration ?? 0) * 100)}%</dd></>
          )}
          {node.score != null && (
            <><dt className="text-slate-500">Score</dt><dd>{node.score.toFixed(2)}</dd></>
          )}
          {node.prior_role && (
            <><dt className="col-span-2 text-slate-500">Prior role</dt><dd className="col-span-2 text-slate-700">{node.prior_role}</dd></>
          )}
        </dl>
      )}
      <h3 className="mb-2 text-base font-semibold uppercase tracking-wider text-slate-500">
        Connections ({incident.length})
      </h3>
      <ul className="space-y-1 text-sm">
        {incident.slice(0, 30).map((l, i) => {
          const otherId =
            (typeof l.source === "string" ? l.source : l.source.id) === node.id
              ? typeof l.target === "string" ? l.target : l.target.id
              : typeof l.source === "string" ? l.source : l.source.id
          const other = nodeById.get(otherId)
          if (!other) return null
          return (
            <li key={`${otherId}-${i}`} className="flex items-baseline gap-2">
              <span
                className="inline-block h-2 w-2 shrink-0 rounded-full"
                style={{ backgroundColor: l.color }}
                aria-hidden
              />
              <span className="text-slate-500">{l.type}</span>
              <span className="text-slate-900">{other.label}</span>
              {l.type === "funded_by" && l.weight ? (
                <span className="ml-auto font-mono tabular-nums text-emerald-700">
                  {fmtUSD(l.weight)}
                </span>
              ) : null}
              {l.type === "mentions" && l.weight ? (
                <span className="ml-auto tabular-nums text-amber-700">
                  ×{l.weight}
                </span>
              ) : null}
            </li>
          )
        })}
      </ul>
      {incident.some((l) => l.latest_url) && (
        <div className="mt-3 border-t border-slate-100 pt-3 text-sm">
          <p className="mb-1 font-semibold text-slate-700">Latest press-release mention</p>
          {(() => {
            const latest = incident.find((l) => l.latest_url)
            if (!latest || !latest.latest_url) return null
            return (
              <a
                href={latest.latest_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-indigo-600 underline decoration-dotted hover:text-indigo-800"
              >
                {latest.latest_date}: {latest.latest_title}
              </a>
            )
          })()}
        </div>
      )}
    </aside>
  )
}

// ── Main client component ──────────────────────────────────────────────────────

export default function GraphClient({ initialData }: { initialData: CoiGraphPayload }) {
  const [data, setData] = useState<CoiGraphPayload>(initialData)
  const [refreshing, setRefreshing] = useState(false)
  const [refreshedAt, setRefreshedAt] = useState<Date | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [visibleTypes, setVisibleTypes] = useState<Set<NodeType>>(new Set(NODE_TYPES))
  const [selectedNode, setSelectedNode] = useState<CoiNode | null>(null)

  const refresh = async () => {
    setRefreshing(true)
    setError(null)
    try {
      const res = await fetch(`/coi_graph.json?ts=${Date.now()}`, { cache: "no-store" })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const next = (await res.json()) as CoiGraphPayload
      setData(next)
      setRefreshedAt(new Date())
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRefreshing(false)
    }
  }

  const toggleType = (t: NodeType) => {
    setVisibleTypes((prev) => {
      const next = new Set(prev)
      if (next.has(t)) next.delete(t)
      else next.add(t)
      return next
    })
  }

  const counts = useMemo(() => {
    const c: Record<string, number> = {}
    for (const n of data.nodes) c[n.type] = (c[n.type] || 0) + 1
    return c
  }, [data.nodes])

  return (
    <>
      {/* Refresh strip */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3 rounded-xl border border-slate-200 bg-white px-5 py-4">
        <button
          onClick={refresh}
          disabled={refreshing}
          className={clsx(
            "inline-flex items-center gap-2 rounded-lg px-4 py-2 text-base font-semibold transition",
            refreshing
              ? "bg-slate-100 text-slate-400"
              : "bg-indigo-600 text-white hover:bg-indigo-700"
          )}
        >
          {refreshing ? "Refreshing…" : "↻ Refresh graph"}
        </button>
        <div className="text-sm text-slate-500">
          {error && <span className="font-semibold text-rose-700">refresh failed: {error}</span>}
          {!error && refreshedAt && <span>Last refresh: {refreshedAt.toLocaleTimeString()}</span>}
          {!error && !refreshedAt && (
            <span>
              <strong className="text-slate-900">{data.n_findings_included}</strong>{" "}
              scan findings included · graph generated {new Date(data.generated_at).toLocaleString()}
            </span>
          )}
        </div>
      </div>

      <TrianglesPanel triangles={data.triangles || []} />

      {/* Filter chips */}
      <div className="mb-4 flex flex-wrap items-center gap-2">
        <span className="text-sm font-semibold uppercase tracking-wider text-slate-500">
          Show
        </span>
        {NODE_TYPES.map((t) => {
          const active = visibleTypes.has(t)
          const color = data.legend.find((l) => l.type === t)?.color ?? "#64748b"
          return (
            <button
              key={t}
              onClick={() => toggleType(t)}
              className={clsx(
                "inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-semibold ring-1 transition",
                active
                  ? "bg-white text-slate-900 ring-slate-300"
                  : "bg-slate-100 text-slate-400 ring-slate-200"
              )}
              aria-pressed={active}
            >
              <span
                className="inline-block h-3 w-3 rounded-full"
                style={{ backgroundColor: color, opacity: active ? 1 : 0.4 }}
                aria-hidden
              />
              {TYPE_LABELS[t]} <span className="opacity-60">({counts[t] || 0})</span>
            </button>
          )
        })}
      </div>

      {/* Graph + inspector grid */}
      <div className="grid gap-6 lg:grid-cols-[1fr_360px]">
        <div>
          <ForceGraph
            data={data}
            visibleTypes={visibleTypes}
            onNodeClick={setSelectedNode}
            selectedNodeId={selectedNode?.id ?? null}
          />
          <p className="mt-2 text-sm text-slate-500">
            Click a node to inspect · scroll to zoom · drag the background to pan ·
            drag a node to pin it.
          </p>
        </div>
        <div>
          {selectedNode ? (
            <NodeInspector node={selectedNode} links={data.links} nodes={data.nodes} />
          ) : (
            <aside className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-6 text-center text-slate-500">
              <p className="text-base font-semibold text-slate-700">No node selected</p>
              <p className="mt-1 text-sm">
                Click any node in the graph to see its connections, prior role,
                and latest press-release mention.
              </p>
            </aside>
          )}
        </div>
      </div>

      {/* Hubs + Bridges below */}
      {data.hubs?.length > 0 && (
        <section className="mt-8 rounded-xl border border-emerald-200 bg-emerald-50 p-5">
          <h2 className="mb-3 text-2xl">Hubs ({data.hubs.length})</h2>
          <p className="mb-4 text-base text-slate-700">
            Clients receiving both agency dollars and legislator mentions. Hub score
            = log₁₀(dollars + 1) × mentions.
          </p>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-base">
              <thead className="bg-slate-50">
                <tr className="text-left text-sm uppercase tracking-wider text-slate-600">
                  <th className="px-4 py-2 font-semibold">Client</th>
                  <th className="px-4 py-2 font-semibold">Agencies</th>
                  <th className="px-4 py-2 text-right font-semibold">Dollars</th>
                  <th className="px-4 py-2 text-right font-semibold">Mentions</th>
                  <th className="px-4 py-2 text-right font-semibold">Score</th>
                </tr>
              </thead>
              <tbody>
                {data.hubs.slice(0, 15).map((h) => (
                  <tr key={h.client} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-semibold text-emerald-800">{h.client}</td>
                    <td className="px-4 py-2 text-rose-700">{h.agencies.join(", ")}</td>
                    <td className="px-4 py-2 text-right font-mono tabular-nums">{fmtUSD(h.dollars)}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{h.n_mentions}</td>
                    <td className="px-4 py-2 text-right tabular-nums font-semibold">{h.score}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}

      {data.bridges?.length > 0 && (
        <section className="mt-6 rounded-xl border border-indigo-200 bg-indigo-50 p-5">
          <h2 className="mb-3 text-2xl">Bridges ({data.bridges.length})</h2>
          <p className="mb-4 text-base text-slate-700">
            Clients shared by two or more lobbyists in the top-N scan — possible
            focal points for a wider story.
          </p>
          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="w-full text-base">
              <thead className="bg-slate-50">
                <tr className="text-left text-sm uppercase tracking-wider text-slate-600">
                  <th className="px-4 py-2 font-semibold">Client</th>
                  <th className="px-4 py-2 text-right font-semibold"># Lobbyists</th>
                  <th className="px-4 py-2 font-semibold">Lobbyists</th>
                </tr>
              </thead>
              <tbody>
                {data.bridges.slice(0, 15).map((b) => (
                  <tr key={b.client} className="border-t border-slate-100">
                    <td className="px-4 py-2 font-semibold text-indigo-800">{b.client}</td>
                    <td className="px-4 py-2 text-right tabular-nums">{b.n_lobbyists}</td>
                    <td className="px-4 py-2 text-slate-700">{b.lobbyists.join(", ")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      )}
    </>
  )
}
