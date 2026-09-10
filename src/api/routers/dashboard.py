"""Landing-view aggregate and the endpoints stubbed for the demo."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

import pandas as pd
from fastapi import APIRouter, HTTPException, Query, Request

from src.api.errors import NotImplementedInDemo
from src.api.state import FORECAST_MODEL_VERSION, SHORTFALL_MODEL_VERSION
from src.reference.moil_mines import MOIL_MINES

logger = logging.getLogger("api.dashboard")

router = APIRouter(tags=["dashboard"])


@router.get("/dashboard/summary", summary="Aggregated landing-view data")
def get_dashboard_summary(request: Request) -> dict[str, Any]:
    """One call for the landing page, composed from the other endpoints.

    The component functions are called directly rather than over HTTP, so each
    hits its own memoised payload. That also means composed latency is the sum
    of three cache reads (single-digit milliseconds), not the sum of three cold
    computations - `asyncio.gather` would add scheduling overhead without
    removing any wait, since nothing here is I/O bound once warm.

    A component that fails leaves its block explicitly `null` and names itself
    in `degraded`. The key is always present: a missing key and a null key
    behave differently in a TypeScript client, and the contract promises null.
    """
    from src.api.routers.forecast import get_forecast
    from src.api.routers.shortfall import get_shortfall_risk

    artifacts = request.app.state.artifacts
    degraded: list[str] = []

    latest_actual: dict[str, Any] | None = None
    series_health: dict[str, Any] | None = None
    try:
        frame = artifacts.require("production_series").sort_values("report_month")
        last = frame.iloc[-1]
        latest_actual = {
            "month": str(last.report_month),
            "mh_plus_mp_tonnes": float(last.mh_plus_mp_qty_tonnes),
            "all_india_tonnes": float(last.all_india_qty_tonnes),
        }
        expected = pd.period_range(frame.report_month.min(), frame.report_month.max(), freq="M")
        present = set(frame.report_month)
        series_health = {
            "months_present": int(len(frame)),
            "months_missing": int(sum(1 for p in expected if p not in present)),
            "date_range": {
                "start": str(frame.report_month.min()),
                "end": str(frame.report_month.max()),
            },
            "ocr_recovered_months": int((frame.extraction_method == "tesseract_ocr").sum()),
        }
    except Exception as exc:  # noqa: BLE001 - one block must not blank the page
        logger.warning("dashboard: production series unavailable: %s", exc)
        degraded.append("production")

    next_forecast: dict[str, Any] | None = None
    best_horizon: dict[str, Any] | None = None
    try:
        forecast = get_forecast(request, horizon=1)
        next_forecast = {
            "month": forecast["target_period"],
            "predicted_tonnes": forecast["predicted_tonnes"],
            "lower_ci": forecast["predicted_lower_ci"],
            "upper_ci": forecast["predicted_upper_ci"],
            "ci_level": forecast["ci_level"],
        }
        metrics = artifacts.require("forecast_metrics")
        best = metrics.loc[metrics.skill_vs_naive_pp.idxmax()]
        best_horizon = {
            "horizon_months": int(best.horizon_months),
            "mape": float(best.mape),
            "skill_vs_naive_pp": float(best.skill_vs_naive_pp),
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("dashboard: forecast unavailable: %s", exc)
        degraded.append("forecast")

    shortfall: dict[str, Any] | None = None
    try:
        risk = get_shortfall_risk(request)
        shortfall = {
            "month": risk["forecast_month"],
            "probability": risk["shortfall_probability"],
            "risk_level": risk["risk_level"],
        }
    except Exception as exc:  # noqa: BLE001
        logger.warning("dashboard: shortfall unavailable: %s", exc)
        degraded.append("shortfall")

    return {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "latest_actual": latest_actual,
        "next_forecast": next_forecast,
        "shortfall": shortfall,
        "series_health": series_health,
        "model_health": {
            "forecast_version": FORECAST_MODEL_VERSION,
            "shortfall_version": SHORTFALL_MODEL_VERSION,
            "best_horizon": best_horizon,
        },
        "mines": {
            "total": len(MOIL_MINES),
            "underground": sum(
                1 for m in MOIL_MINES.values() if m["mine_type"] == "underground"
            ),
            "opencast": sum(1 for m in MOIL_MINES.values() if m["mine_type"] == "opencast"),
        },
        "degraded": degraded,
    }


@router.get("/recommendations", summary="Rules-engine recommendations (Bucket 2)")
def get_recommendations(
    mine_name: str | None = Query(None),
    limit: int = Query(5, description="1-20"),
) -> dict[str, Any]:
    """Not built yet - returns 501 rather than a plausible-looking fake.

    Params are still validated so the frontend can exercise its error handling
    against the real contract before the engine exists.
    """
    if mine_name is not None and mine_name not in MOIL_MINES:
        raise HTTPException(
            status_code=422,
            detail=f"unknown mine {mine_name!r}; expected one of {', '.join(sorted(MOIL_MINES))}",
        )
    if not 1 <= limit <= 20:
        raise HTTPException(status_code=422, detail=f"limit must be 1-20, got {limit}")

    raise NotImplementedInDemo(
        detail="the recommendations rules engine is not implemented yet (Bucket 2)",
        remedy="mock against the documented shape in docs/phase_4/api_contracts.md section 8",
    )
