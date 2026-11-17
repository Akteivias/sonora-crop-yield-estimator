from __future__ import annotations

import json
import math
import os
import pickle
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field

ROOT_DIR = Path(__file__).resolve().parent
MODEL_PATH = Path(os.getenv("MODEL_PATH", ROOT_DIR / "model.bin"))
METADATA_PATH = Path(os.getenv("METADATA_PATH", ROOT_DIR / "model_metadata.json"))

# Security: model.bin is generated locally by train.py; never load untrusted pickle artifacts.
with MODEL_PATH.open("rb") as f:
    model = pickle.load(f)

KNOWN_CATEGORIES: dict[str, set[str]] = {}
if METADATA_PATH.exists():
    meta = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
    KNOWN_CATEGORIES = {k: set(v) for k, v in meta.get("known_categories", {}).items()}

app = FastAPI(title="Sonora Crop-Yield Estimator")


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    # Starlette's JSONResponse rejects non-finite floats (inf/nan) in Pydantic's error 'input'.
    safe_errors = []
    for err in exc.errors():
        cleaned = dict(err)
        if isinstance(cleaned.get("input"), float) and not math.isfinite(cleaned["input"]):
            cleaned["input"] = str(cleaned["input"])
        safe_errors.append(cleaned)
    return JSONResponse(status_code=422, content={"detail": safe_errors})


class CropPlan(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    Nommunicipio: str = Field(min_length=1, max_length=100)
    Nomcicloproductivo: str = Field(min_length=1, max_length=100)
    Nommodalidad: str = Field(min_length=1, max_length=100)
    Nomcultivo: str = Field(min_length=1, max_length=100)
    Sembrada: float = Field(gt=0, le=42_000.0, allow_inf_nan=False)


@app.post("/predict")
def predict(plan: CropPlan) -> dict[str, Any]:
    payload = plan.model_dump()

    input_warnings: list[str] = []
    for col, known in KNOWN_CATEGORIES.items():
        if payload[col] not in known:
            input_warnings.append(
                f"Unseen {col}='{payload[col]}' in 2021-2024 refit data; "
                "OneHotEncoder(handle_unknown='ignore') encodes it as all-zero features."
            )

    df = pd.DataFrame([payload])
    pred = max(0.0, float(model.predict(df)[0]))
    return {
        "predicted_yield_ton_per_ha": round(pred, 4),
        "input_warnings": input_warnings,
        "note": (
            "Informational pre-harvest estimate based on historical SIAP Sonora records; "
            "not a financial, insurance, or production guarantee."
        ),
    }
