.PHONY: dev test lint fmt seed-dora seed-demo demo reset-graph neo4j-up neo4j-down smoke pipeline frontend

# ── Dev server ────────────────────────────────────────────────────────────────
dev:
	uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# ── Tests ─────────────────────────────────────────────────────────────────────
test:
	uv run pytest tests/ -v

smoke:
	uv run python scripts/test_smoke.py

pipeline:
	uv run python scripts/test_pipeline.py

frontend:
	cd frontend && npm run dev

test-unit:
	uv run pytest tests/unit/ -v

test-integration:
	uv run pytest tests/integration/ -v

# ── Lint / format ─────────────────────────────────────────────────────────────
lint:
	uv run ruff check app/ tests/

fmt:
	uv run ruff format app/ tests/

# ── Data seeding ──────────────────────────────────────────────────────────────
seed-dora:
	uv run python scripts/seed_dora.py

seed-demo:
	uv run python scripts/seed_demo_contracts.py

demo: seed-dora seed-demo

reset-graph:
	uv run python scripts/reset_neo4j.py

# ── Infrastructure ────────────────────────────────────────────────────────────
neo4j-up:
	docker compose up -d neo4j

neo4j-down:
	docker compose down
