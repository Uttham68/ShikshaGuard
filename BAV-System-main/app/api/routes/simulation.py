from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.database.models import School, Proposal
from app.services.simulation_service import simulate_impact

router = APIRouter(prefix="/simulation", tags=["Simulation"])

@router.post("/{proposal_id}")
def run_simulation(proposal_id: int, db: Session = Depends(get_db)):
    proposal = db.query(Proposal).filter(Proposal.id == proposal_id).first()
    if not proposal:
        return {"error": "Proposal not found"}

    school = db.query(School).filter(
        School.pseudocode == proposal.school_pseudocode
    ).first()

    if not school:
        return {"error": "School not found"}

    result = simulate_impact(
        school.__dict__,
        {
            "classrooms_requested": proposal.classrooms_requested
        }
    )

    return result