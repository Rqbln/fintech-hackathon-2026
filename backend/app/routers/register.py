from fastapi import APIRouter

router = APIRouter()


@router.get("/")
async def get_register():
    """Get the DORA Register of Information (RoI) with all vendor entries."""
    # TODO: Aggregate data from all analyzed contracts
    return {"register_entries": [], "total_vendors": 0, "compliance_rate": 0.0}


@router.get("/export")
async def export_register():
    """Export the Register of Information in regulatory format (xBRL-CSV)."""
    # TODO: Generate export
    return {"status": "export_not_implemented"}
