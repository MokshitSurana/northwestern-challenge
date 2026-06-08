/**
 * /glossary — plain-English definitions for the acronyms, statutes, and
 * tradecraft terms FairGuard uses. Every entry has a stable anchor so it
 * can be linked from anywhere in the UI.
 */

import Link from "next/link"

export const metadata = {
  title: "Glossary — FairGuard",
  description:
    "Plain-English definitions: LDA, §207, ALI, covered position, " +
    "discretionary award, BIL, and more.",
}

type Term = {
  id: string
  term: string
  short?: string
  body: React.ReactNode
  seeAlso?: { href: string; label: string }[]
  group: "statutes" | "datasets" | "fields" | "money" | "fairguard"
}

const TERMS: Term[] = [
  // ── Statutes ──────────────────────────────────────────────────────────
  {
    id: "section-207",
    term: "§207 (Section 207 of Title 18)",
    short: "Federal cooling-off statute",
    group: "statutes",
    body: (
      <>
        <p className="mb-2">
          <strong>18 U.S.C. §207</strong> is the federal post-employment conflict-of-interest
          statute. It bars former federal officials from lobbying their old
          agency (or in some cases the entire executive branch) for a defined
          cooling-off period after leaving government.
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li><strong>§207(a):</strong> Permanent ban on switching sides on a matter you personally handled.</li>
          <li><strong>§207(c):</strong> 1-year bar on senior officials contacting their former agency, regardless of subject.</li>
          <li><strong>§207(d):</strong> 2-year bar on very-senior officials contacting the agencies they coordinated.</li>
          <li><strong>§207(b), (f):</strong> Special restrictions on trade-rep, treasury, and foreign-influence work.</li>
        </ul>
        <p className="mt-2">
          The LDA does not record the exact date a lobbyist&apos;s federal employment
          ended, so FairGuard cannot close this gate automatically. Confirm via
          the agency&apos;s OIG report or news coverage of the personnel move.
        </p>
      </>
    ),
    seeAlso: [{ href: "/methods#gates", label: "The four editorial gates" }],
  },
  {
    id: "lda",
    term: "LDA (Lobbying Disclosure Act)",
    short: "1995 statute requiring quarterly lobbying disclosures",
    group: "statutes",
    body: (
      <>
        <p>
          The <strong>Lobbying Disclosure Act of 1995</strong> requires every
          paid lobbyist with more than <em>de minimis</em> federal contact to
          register and file a quarterly disclosure with the U.S. Senate and U.S.
          House. Filings name the lobbyist, their firm (the &ldquo;registrant&rdquo;),
          the client paying them, the federal agencies contacted, the issues
          raised, and the income received.
        </p>
        <p className="mt-2">
          The Senate publishes LDA filings as bulk JSON dumps; the House
          publishes them as XML. FairGuard ingests both via the index skill.
        </p>
      </>
    ),
    seeAlso: [{ href: "/methods#skill-index", label: "How the index skill works" }],
  },
  {
    id: "section-1602",
    term: "§1602 (Lobbying Disclosure Act terminology)",
    short: "Statutory definition of \"lobbying contact\"",
    group: "statutes",
    body: (
      <p>
        The definitional section of the LDA. Sets out what counts as a{" "}
        <em>lobbying contact</em> (oral or written communication on behalf of a
        client to a covered executive- or legislative-branch official) and what
        is exempted (testimony, public comment, requests for information). This
        is the line between a registrable lobbyist and a non-registrable advocate.
      </p>
    ),
  },

  // ── Datasets ──────────────────────────────────────────────────────────
  {
    id: "usaspending",
    term: "USAspending.gov",
    short: "Federal award database",
    group: "datasets",
    body: (
      <p>
        The U.S. Treasury&apos;s public database of federal awards — contracts,
        grants, loans, and direct payments — required by the Federal Funding
        Accountability and Transparency Act. FairGuard&apos;s trace skill
        queries this to see how much federal money flows from a target agency
        to a lobbyist&apos;s clients.
      </p>
    ),
    seeAlso: [{ href: "/methods#skill-trace", label: "How the trace skill works" }],
  },
  {
    id: "bioguide",
    term: "bioguide_id",
    short: "Stable ID for every member of Congress",
    group: "datasets",
    body: (
      <p>
        A short alphanumeric identifier (e.g.{" "}
        <code className="rounded bg-slate-100 px-1 font-mono text-sm">L000174</code>{" "}
        for Sen. Patrick Leahy) maintained by the Bioguide project, used as the
        primary key for legislators across federal datasets. FairGuard keys
        congressional press releases on this so a member&apos;s name change or
        chamber-switch does not break joins.
      </p>
    ),
  },

  // ── Field-level ────────────────────────────────────────────────────────
  {
    id: "covered-position",
    term: "covered position",
    short: "Lobbyist's prior federal role, self-reported",
    group: "fields",
    body: (
      <>
        <p>
          A free-text field in every LDA filing where the lobbyist names the
          covered executive- or legislative-branch positions they held in the
          last 20 years. Example:
        </p>
        <blockquote className="my-2 rounded-lg border-l-4 border-slate-300 bg-slate-50 px-4 py-2 font-mono text-sm text-slate-700">
          Senior Advisor - Department of Energy (DOE); Office Director - (DOE)
        </blockquote>
        <p>
          This is <strong>self-disclosure</strong> — the Senate does not verify
          it. Always confirm against an agency staff directory or news archive
          before publication.
        </p>
      </>
    ),
    seeAlso: [{ href: "/methods#gates", label: "Gate 1 — Prior agency role" }],
  },
  {
    id: "registrant",
    term: "registrant",
    short: "The firm filing on behalf of a client",
    group: "fields",
    body: (
      <p>
        The lobbying firm (or in-house lobbying unit) that files the LDA
        disclosure. A registrant employs lobbyists and represents one or more
        clients. FairGuard shows this as <em>&ldquo;Firm&rdquo;</em> in finding cards.
      </p>
    ),
  },
  {
    id: "ali-code",
    term: "ALI code (Issue Area code)",
    short: "Three-letter category for the lobbying topic",
    group: "fields",
    body: (
      <>
        <p>
          The LDA uses ~80 three-letter <strong>Issue Area</strong> codes to
          categorize what was lobbied. Examples:
        </p>
        <ul className="ml-5 list-disc space-y-1">
          <li><code className="rounded bg-slate-100 px-1 font-mono text-sm">TAX</code> — Taxation</li>
          <li><code className="rounded bg-slate-100 px-1 font-mono text-sm">ENG</code> — Energy and Nuclear</li>
          <li><code className="rounded bg-slate-100 px-1 font-mono text-sm">AGR</code> — Agriculture</li>
          <li><code className="rounded bg-slate-100 px-1 font-mono text-sm">HCR</code> — Health Issues</li>
        </ul>
        <p className="mt-2">
          House filings carry the code in <em>two</em> schemas (modern{" "}
          <code className="rounded bg-slate-100 px-1 font-mono text-xs">ali_info/issueAreaCode</code>{" "}
          vs legacy <code className="rounded bg-slate-100 px-1 font-mono text-xs">ali_Code</code>);
          parse both or you lose ~30% of activities.
        </p>
      </>
    ),
  },
  {
    id: "filing-uuid",
    term: "filing UUID",
    short: "Stable Senate-LDA identifier for one filing",
    group: "fields",
    body: (
      <>
        <p>
          The primary key for a Senate LDA filing. Every finding card shows the
          first 8 characters and links to the full filing at{" "}
          <a
            href="https://lda.senate.gov/"
            target="_blank"
            rel="noopener noreferrer"
            className="font-mono text-indigo-700 underline decoration-dotted hover:text-indigo-900"
          >
            lda.senate.gov
          </a>.
          Example URL:
        </p>
        <pre className="my-2 overflow-x-auto rounded bg-slate-100 px-3 py-2 font-mono text-xs text-slate-700">
{`https://lda.senate.gov/filings/public/filing/<UUID>/print/`}
        </pre>
        <p>
          House filings have a parallel <code className="rounded bg-slate-100 px-1 font-mono text-sm">house_id</code>{" "}
          that joins to the Senate UUID at the firm-engagement level (not the filing level).
        </p>
      </>
    ),
  },
  {
    id: "concentration",
    term: "agency concentration ratio",
    short: "Share of a lobbyist's filings targeting one agency",
    group: "fields",
    body: (
      <p>
        FairGuard&apos;s ranking signal. If a lobbyist files 213 of their 236
        total quarterly disclosures naming the Department of Energy, their
        concentration on DOE is <strong>213/236 = 90%</strong>. A high
        concentration plus a prior covered position at the same agency is the{" "}
        <em>Bridenstine pattern</em> — a structural conflict-of-interest signal
        worth investigating.
      </p>
    ),
    seeAlso: [{ href: "/methods#skill-scan", label: "How the scan skill works" }],
  },

  // ── Money ─────────────────────────────────────────────────────────────
  {
    id: "discretionary",
    term: "discretionary vs routine awards",
    short: "Newsworthy core vs context",
    group: "money",
    body: (
      <>
        <p>
          FairGuard&apos;s trace skill splits federal awards into two buckets:
        </p>
        <ul className="ml-5 list-disc space-y-2">
          <li>
            <strong>Discretionary</strong> — competitively awarded grants
            (e.g. DOE Battery Materials Processing Grants, EPA EPCRA grants).
            An agency official picks among applicants. <em>Newsworthy core.</em>
          </li>
          <li>
            <strong>Routine</strong> — formulaic program participation:
            commodity purchases (USDA AMS), food aid (USAID), rural utilities
            financing (USDA RUS). Largely automatic if you qualify. <em>Context.</em>
          </li>
        </ul>
        <p className="mt-2">
          Why it matters: $700M of routine USDA commodity purchases tells you a
          company is big, not that a lobbyist&apos;s influence won them anything.
          $200M of discretionary DOE grants tells you something an agency
          officer chose to give. Frame accordingly.
        </p>
      </>
    ),
    seeAlso: [{ href: "/methods#skill-trace", label: "How the trace skill works" }],
  },
  {
    id: "bil",
    term: "BIL (Bipartisan Infrastructure Law)",
    short: "Public Law 117-58",
    group: "money",
    body: (
      <p>
        The 2021 <strong>Infrastructure Investment and Jobs Act</strong>, often
        shortened to BIL. Authorized ~$1.2T of federal spending — and ~$550B of
        <em> new</em> spending — across roads, bridges, power grid, broadband,
        EV charging, and critical-minerals supply chains. Many of the largest
        discretionary awards in FairGuard&apos;s money trails are BIL-funded.
      </p>
    ),
  },
  {
    id: "ira",
    term: "IRA (Inflation Reduction Act)",
    short: "Public Law 117-169",
    group: "money",
    body: (
      <p>
        The 2022 <strong>Inflation Reduction Act</strong>. Authorized ~$370B of
        climate and clean-energy spending and tax credits. Like BIL, many
        battery / critical-minerals / EV awards traced by FairGuard sit in IRA
        program codes.
      </p>
    ),
  },
  {
    id: "spv",
    term: "SPV (special-purpose vehicle)",
    short: "Subsidiary entity created for one project",
    group: "money",
    body: (
      <p>
        A separately-incorporated subsidiary, often used for a single grant or
        project. Example:{" "}
        <code className="rounded bg-slate-100 px-1 font-mono text-sm">GROUP14 BAM-2, INC.</code>{" "}
        is an SPV of Group14 Technologies created for one DOE Battery Materials
        Processing grant. FairGuard&apos;s trace skill is explicit about keeping
        same-company SPVs (a lobbyist&apos;s win) and excluding coincidental
        name collisions (e.g. <em>ICL Specialty Products</em> vs <em>ICL-IP America</em>).
      </p>
    ),
  },

  // ── FairGuard-specific ────────────────────────────────────────────────
  {
    id: "bridenstine-pattern",
    term: "Bridenstine pattern",
    short: "Former agency head returns as paid lobbyist",
    group: "fairguard",
    body: (
      <p>
        Named after Jim Bridenstine, NASA Administrator under the first Trump
        administration, who returned in 2022 as a registered lobbyist via The
        Artemis Group. Filings now name NASA in roughly 39% of his quarterly
        disclosures. The pattern — a former senior official directing a
        disproportionate share of their lobbying back at their old agency — is
        what FairGuard&apos;s scan skill ranks. Bridenstine&apos;s case is the
        repo&apos;s anchor finding (verified in{" "}
        <code className="rounded bg-slate-100 px-1 font-mono text-sm">notes/05_finding_bridenstine.md</code>).
      </p>
    ),
  },
  {
    id: "triangle",
    term: "triangle (conflict-of-interest)",
    short: "Three-way edge: legislator ↔ client ↔ agency",
    group: "fairguard",
    body: (
      <p>
        The coi-graph skill flags triangles: a legislator who has named a client
        in a press release, that client&apos;s agency that issued them a
        discretionary award, and the lobbying firm representing the client to
        the agency. Three independent signals on the same client. Triangles are
        the highest-priority leads in <Link href="/graph" className="font-semibold text-indigo-700 underline decoration-dotted">/graph</Link>.
      </p>
    ),
  },
  {
    id: "hub",
    term: "hub (conflict-of-interest)",
    short: "Client connected to many lobbyists",
    group: "fairguard",
    body: (
      <p>
        A client (e.g. Cargill, ICL) represented by many distinct registered
        lobbyists across multiple agencies. Hubs surface companies that
        coordinate a wide influence campaign, even when no single lobbying
        relationship is unusual.
      </p>
    ),
  },
  {
    id: "bridge",
    term: "bridge (conflict-of-interest)",
    short: "Client linking two otherwise-unrelated cases",
    group: "fairguard",
    body: (
      <p>
        A client that appears under two different revolving-door candidates,
        forming a bridge between cases. Useful for spotting industry coalitions
        and for sizing a planned story&apos;s scope (one case, or several?).
      </p>
    ),
  },
  {
    id: "verification-status",
    term: "verification status",
    short: "FairGuard's per-finding confidence flag",
    group: "fairguard",
    body: (
      <>
        <p>Three levels:</p>
        <ul className="ml-5 list-disc space-y-1">
          <li><strong>verified</strong> — prior role independently confirmed (CFTC.gov, USDA, etc.)</li>
          <li><strong>partial</strong> — some signals confirmed, others outstanding</li>
          <li><strong>unverified</strong> — only the LDA self-disclosure exists</li>
        </ul>
        <p className="mt-2">
          The badge appears on each finding card. Most candidates are unverified
          by default; <code className="rounded bg-slate-100 px-1 font-mono text-sm">notes/08_external_verification_top_candidates.md</code>{" "}
          documents the top-10 verifications.
        </p>
      </>
    ),
  },
]

const GROUP_LABEL: Record<Term["group"], string> = {
  statutes: "Statutes and law",
  datasets: "Data sources",
  fields: "LDA field names",
  money: "Money and awards",
  fairguard: "FairGuard tradecraft",
}

export default function Page() {
  const grouped: Record<Term["group"], Term[]> = {
    statutes: [], datasets: [], fields: [], money: [], fairguard: [],
  }
  for (const t of TERMS) grouped[t.group].push(t)

  return (
    <div className="max-w-4xl">
      <header className="mb-10">
        <h1 className="mb-4">Glossary</h1>
        <p className="text-xl leading-relaxed text-slate-700">
          Plain-English definitions for the acronyms, statutes, and tradecraft
          terms FairGuard uses. Every entry has a stable anchor so it can be
          linked from anywhere in the UI — try{" "}
          <Link href="/glossary#section-207" className="font-semibold text-indigo-700 underline decoration-dotted">/glossary#section-207</Link>{" "}
          or <Link href="/glossary#discretionary" className="font-semibold text-indigo-700 underline decoration-dotted">/glossary#discretionary</Link>.
        </p>
      </header>

      {/* TOC */}
      <nav className="mb-12 rounded-xl border border-slate-200 bg-slate-50 p-5">
        <p className="mb-3 text-sm font-semibold uppercase tracking-wider text-slate-500">
          Jump to
        </p>
        <div className="grid gap-1 sm:grid-cols-2">
          {(Object.keys(grouped) as Term["group"][]).map((g) => (
            <a
              key={g}
              href={`#group-${g}`}
              className="text-base font-semibold text-indigo-700 underline decoration-dotted hover:text-indigo-900"
            >
              {GROUP_LABEL[g]} ({grouped[g].length})
            </a>
          ))}
        </div>
      </nav>

      {(Object.keys(grouped) as Term["group"][]).map((g) => (
        <section key={g} id={`group-${g}`} className="mb-14 scroll-mt-32">
          <h2 className="mb-5">{GROUP_LABEL[g]}</h2>
          <div className="space-y-5">
            {grouped[g].map((t) => (
              <article
                key={t.id}
                id={t.id}
                className="scroll-mt-32 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
              >
                <header className="mb-3 flex flex-wrap items-baseline gap-3">
                  <h3 className="text-xl font-bold text-slate-900">{t.term}</h3>
                  {t.short && (
                    <span className="text-base italic text-slate-500">— {t.short}</span>
                  )}
                  <a
                    href={`#${t.id}`}
                    className="ml-auto text-sm text-slate-400 hover:text-indigo-600"
                    aria-label={`Permalink to ${t.term}`}
                    title="Permalink"
                  >
                    #
                  </a>
                </header>
                <div className="text-base leading-relaxed text-slate-700">{t.body}</div>
                {t.seeAlso && t.seeAlso.length > 0 && (
                  <footer className="mt-4 border-t border-slate-100 pt-3 text-sm">
                    <span className="font-semibold uppercase tracking-wider text-slate-500">
                      See also:
                    </span>{" "}
                    {t.seeAlso.map((s, i) => (
                      <span key={s.href}>
                        <Link
                          href={s.href}
                          className="font-semibold text-indigo-700 underline decoration-dotted hover:text-indigo-900"
                        >
                          {s.label}
                        </Link>
                        {i < t.seeAlso!.length - 1 && <span className="text-slate-400">, </span>}
                      </span>
                    ))}
                  </footer>
                )}
              </article>
            ))}
          </div>
        </section>
      ))}
    </div>
  )
}
