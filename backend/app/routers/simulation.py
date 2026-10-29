"""
Fairness simulation router — deterministic synthetic demand replay.
Compares First-Come, First-Served against OpenBench Allocation Policy.
"""
from fastapi import APIRouter, Query
from app.services.fairness_simulator_service import run_fairness_simulation

router = APIRouter(prefix="/fairness-simulator", tags=["fairness-simulator"])


@router.get("/run")
def get_simulation_run(
    seed: int = Query(default=42, description="RNG Seed for deterministic synthetic replay"),
    days: int = Query(default=30, ge=7, le=90, description="Simulation duration in days"),
):
    """
    Runs a deterministic synthetic replay over the given number of days
    comparing FCFS versus OpenBench policy.
    Clearly flagged as synthetic demand data.
    """
    return run_fairness_simulation(seed=seed, days=days)

