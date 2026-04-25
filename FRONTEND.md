# DORA AI Analyst — Frontend Design Brief

## The core insight: the graph IS the product

Every competitor has a table of controls and a red/amber/green status. The differentiator is the **dependency graph with the bank at the center**. The frontend should make that viscerally clear in the first 5 seconds of the demo. Everything else is a detail panel that slides in from the side.

---

## Recommended stack

| Layer | Choice | Why |
|---|---|---|
| Framework | **Next.js 15 (App Router)** | Fast enough for a demo, easy to deploy on Vercel/Cloud Run, React ecosystem for components |
| Styling | **Tailwind CSS + shadcn/ui** | Pre-built dark-theme components, copy-paste, looks polished in hours not days |
| Graph | **Sigma.js v3 + graphology** | WebGL — handles 500+ nodes at 60fps, the only graph lib that looks genuinely impressive live. Already matches the backend API response format |
| Streaming AI text | **Vercel AI SDK (`useChat`)** | Typewriter effect on LLM output, streaming from the FastAPI backend via SSE |
| PDF citation viewer | **react-pdf** | Highlight the exact cited span in the original PDF — this is the "wow" moment |
| Animations | **Framer Motion** | Slide-in panels, node pulse on risk score update |
| Icons | **Lucide React** | Ships with shadcn |

**What to avoid:** D3.js (too much custom code for a demo), vis.js (already used in test UI, not impressive enough for the real demo), React Flow (it's a node editor, not a graph viz).

---

## Three screens only

### Screen 1 — Upload (30 seconds of demo time)

```
┌─────────────────────────────────────────────┐
│                                             │
│   🏦  Banque Démo SA                        │
│                                             │
│   ┌──────────────────────────────────────┐  │
│   │  Drop your vendor contracts here    │  │
│   │  or click to select multiple PDFs   │  │
│   │                                      │  │
│   │  [drag-and-drop zone, large]         │  │
│   └──────────────────────────────────────┘  │
│                                             │
│   [  Analyse with DORA AI  →  ]            │
│                                             │
└─────────────────────────────────────────────┘
```

- Single button, multiple files at once
- As each file uploads, a live feed appears: `"Extracting AWS contract… ✓"`, `"Building dependency graph… ✓"`, `"Scoring risks…"`
- This typewriter-style feed is the "AI analyst working" moment — not a spinner
- Auto-transitions to Screen 2 when all jobs complete

---

### Screen 2 — The Graph (main demo screen, ~2 minutes)

```
┌──────────────────────────────────────────────────────────────────┐
│  DORA AI Analyst          [Banque Démo SA]    Risk: HIGH  [ECB ↓]│
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│              ╭──────────╮                                        │
│    ○ Equinix │          │ AWS ●  ← big red node, pulsing        │
│              │  🏦 Bank │                                        │
│    ○ Lumen   │ (center) │ Azure ●                               │
│              ╰──────────╯                                        │
│                    │                                             │
│               Cloudflare ○                                       │
│                                                                  │
│  [Legend: ● Critical  ● High  ○ Medium  ○ Low]                 │
└──────────────────────────────────────────────────────────────────┘
```

- **Bank node** at the center, fixed, visually distinct (logo, different shape)
- **Vendor nodes** sized and colored by `criticality_score` — AWS is visually dominant if it's the biggest risk
- **Edge labels**: PROVIDES, DEPENDS_ON, COVERS — thin lines for low risk, thick red for critical dependency
- **Sub-vendor nodes** (Equinix, Lumen) show the 4th-party chain automatically — uploaded from the contract by the ExtractionAgent
- **Live pulse animation** on high-risk nodes (CSS keyframe, red glow)
- **Click any vendor node** → Screen 3 slides in from the right as a panel (graph stays visible, dims 30%)

Key moment: seeing AWS as a giant red pulsing node with 4 services and 2 sub-vendors attached, versus Lumen as a small grey node, tells the risk story instantly without a single table.

---

### Screen 3 — Vendor Gap Analysis Panel (slides in, ~1 minute per vendor)

```
┌──────────────────────────────────────────────────────────────────┐
│ [Graph, dimmed 30%]            ┌────────────────────────────────┐│
│                                │ AWS  ●●●  score: 0.82         ││
│                                │ 3 contracts · 4 services · 🇺🇸  ││
│                                ├────────────────────────────────┤│
│                                │ DORA Art.30 Findings            ││
│                                │                                ││
│                                │ ✅ 2a — Description of services ││
│                                │ ⚠️  2b — Data location         ││
│                                │    └─ Gap: no change notif.   ││
│                                │    └─ "...data shall remain   ││
│                                │        in eu-west-1..."       ││  ← cited excerpt
│                                │       [See in PDF →]          ││  ← opens citation viewer
│                                │                                ││
│                                │ ❌ 3a — Exit strategy          ││
│                                │    └─ Not addressed            ││
│                                │                                ││
│                                │ [ Generate Remediation Plan ]  ││
│                                └────────────────────────────────┘│
└──────────────────────────────────────────────────────────────────┘
```

The **cited excerpt + "See in PDF →"** is the demo killer feature. The original contract PDF opens with that exact sentence highlighted. This is what "AI analyst" means — it shows its work with primary sources, not just a verdict.

---

## The ECB report button

Fixed in the top-right navbar. Clicking it triggers a full-page summary:
- Executive summary (streaming typewriter text)
- Obligation table across all vendors
- Exports to PDF (`react-to-print` or server-side markdown→PDF)

---

## Backend API wiring

The frontend talks to the existing FastAPI backend at `http://localhost:8000`.

| UI action | API call |
|-----------|----------|
| Drop files | `POST /api/ingest` (one call per file, returns `job_id`) |
| Poll pipeline progress | `GET /api/jobs/{job_id}` every 2 s |
| Load graph | `GET /api/graph` → Sigma.js nodes + edges |
| Click vendor node | `POST /api/gap-analysis` with `contract_ids` for that vendor |
| Open PDF citation | Serve PDF from GCS, scroll to cited page |
| Generate remediation | `POST /api/remediation` with `session_id` |
| ECB report | `GET /api/report/{session_id}/markdown` |

The graph API already returns Sigma.js-compatible JSON (`{nodes: [{key, attributes}], edges: [{key, source, target, attributes}]}`). Node `attributes.criticality_score` drives size; `attributes.color` drives color.

---

## Graph node design

| Node type | Shape | Color | Size |
|-----------|-------|-------|------|
| Bank (client) | Hexagon | White / gold | Fixed large |
| Vendor — critical | Circle | `#ef4444` (red) + glow pulse | `criticality_score × 40px` |
| Vendor — high | Circle | `#f59e0b` (amber) | scaled |
| Vendor — medium | Circle | `#6366f1` (indigo) | scaled |
| Service | Diamond | `#22d3ee` (cyan) | Fixed small |
| 4th-party vendor | Circle | `#94a3b8` (grey) | Fixed small |

Edge thickness = relationship weight. DEPENDS_ON edges are dashed.

---

## What to build vs. defer

| Feature | Build for demo | Defer |
|---|---|---|
| Graph with bank at center | ✅ | |
| Multi-file drag-and-drop upload | ✅ | |
| Live AI processing feed (typewriter) | ✅ | |
| Click node → slide panel | ✅ | |
| Verdict badges + gap text + rationale | ✅ | |
| Cited excerpt highlight | ✅ — this is the differentiator | |
| PDF inline viewer with highlight | ✅ if time allows | |
| ECB report button | ✅ (markdown already generated server-side) | |
| Remediation panel with EU alternatives | ✅ | |
| Auth / login | | ✅ |
| Multi-tenant / client switching | | ✅ |
| Real-time streaming from FastAPI SSE | | ✅ — fake with setTimeout if needed |
| Mobile responsive | | ✅ |

---

## One thing to avoid

Do not build a table of controls with red/amber/green dots. That is what every competitor has. The second a VC sees a compliance checkbox table they will say "oh, like Vanta." The graph with the bank at the center and a pulsing AWS node is what makes this an AI analyst, not a dashboard.
