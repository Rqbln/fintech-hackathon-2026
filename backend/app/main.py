from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from app.routers import documents, analysis, alerts, register

app = FastAPI(
    title="RegAgent API",
    description="Multi-agent DORA compliance platform for Third-Party Risk Management",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(documents.router, prefix="/api/documents", tags=["Documents"])
app.include_router(analysis.router, prefix="/api/analysis", tags=["Analysis"])
app.include_router(alerts.router, prefix="/api/alerts", tags=["Alerts"])
app.include_router(register.router, prefix="/api/register", tags=["Register"])


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health")
async def health():
    return {"status": "ok", "service": "regagent"}
