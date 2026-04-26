# Shipper - Frontend Notes

This file documents the current frontend behavior and conventions for the final demo build.

## Stack

- Next.js (App Router)
- React + TypeScript
- Tailwind CSS
- `@xyflow/react` for supply-chain graph
- `lucide-react` icons

## Main routes

- `/` - Dashboard + ingestion hub
- `/graph` - Supply Chain Risk Map
- `/investigation` - Split-screen PDF + streamed analysis
- `/register` - One-line audit register per analyzed document

## UX principles used in the app

- Keep a clean SaaS shell with light color palette
- Put Institution at the center of the graph
- Make findings readable by default (compact cards + expandable details)
- Always tie claims to evidence (source click => PDF highlight)
- Preserve analysis state when user changes tabs/pages

## Graph behavior (`/graph`)

- Custom node cards (not default React Flow nodes)
- Animated edges
- MiniMap + Controls + dot background
- Data sourced from backend `/api/graph`
- Clicking a vendor node opens `/investigation` with query params
- Layout ensures branches originate from Institution

## Investigation behavior (`/investigation`)

- Left: PDF viewer
- Right: streamed non-conformity analysis
- Progress bar shown during streaming
- Source click resolves page and requests highlighted PDF
- Session cache used to avoid unnecessary full re-runs

## Register behavior (`/register`)

- One line per analyzed document/session
- "Voir en detail" deep-links to investigation for that contract/vendor
- Rows are built from `/api/sessions` + `/api/sessions/{id}/trace`

## Deployment notes

- Frontend service name: `shipper-frontend`
- Frontend branding: `Shipper` + `frontend/public/shipper-logo.png`
- API proxy is configured through Next.js rewrites and `BACKEND_API_BASE`

## Common gotchas

- `@xyflow/react` missing: run `npm install` in `frontend/`
- Old UI after deploy: hard refresh browser cache
- 404 on trace/report: stale `session_id` after backend restart
