from __future__ import annotations

import hashlib
import json
import pickle
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, root_mean_squared_error
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT_DIR = Path(__file__).resolve().parent
DATA_PATH = ROOT_DIR / "data" / "sonora_crop_yield_2021_2025.csv"
MANIFEST_PATH = ROOT_DIR / "data_manifest.json"
MODEL_PATH = ROOT_DIR / "model.bin"
METADATA_PATH = ROOT_DIR / "model_metadata.json"

NUM_COLS = ["Sembrada"]
CAT_COLS = ["Nommunicipio", "Nomcicloproductivo", "Nommodalidad", "Nomcultivo"]
FEATURES = NUM_COLS + CAT_COLS
TARGET = "Rendimiento"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def make_preprocessor() -> ColumnTransformer:
    return ColumnTransformer(
        [
            (
                "num",
                Pipeline([("imp", SimpleImputer(strategy="median")), ("sc", StandardScaler())]),
                NUM_COLS,
            ),
            ("cat", OneHotEncoder(handle_unknown="ignore"), CAT_COLS),
        ]
    )


def build_estimator(model_name: str, params: dict[str, Any]) -> Any:
    if model_name == "LinearRegression":
        return LinearRegression(**params)
    if model_name == "RandomForestRegressor":
        return RandomForestRegressor(**params)
    if model_name == "GradientBoostingRegressor":
        return GradientBoostingRegressor(**params)
    raise ValueError(f"Unsupported model_name: {model_name}")


def eval_metrics(y_true: pd.Series, y_pred: np.ndarray) -> dict[str, float]:
    clipped = np.clip(y_pred, 0.0, None)
    return {
        "rmse": round(float(root_mean_squared_error(y_true, clipped)), 4),
        "mae": round(float(mean_absolute_error(y_true, clipped)), 4),
    }


def main() -> None:
    df = pd.read_csv(DATA_PATH)
    train_df = df[df["Anio"] <= 2023].copy()
    val_df = df[df["Anio"] == 2024].copy()
    test_df = df[df["Anio"] == 2025].copy()

    # Baselines evaluated on 2024 validation
    global_mean = float(train_df[TARGET].mean())
    crop_means = train_df.groupby("Nomcultivo")[TARGET].mean().to_dict()
    val_global = eval_metrics(val_df[TARGET], np.full(len(val_df), global_mean))
    val_per_crop = eval_metrics(
        val_df[TARGET], val_df["Nomcultivo"].map(crop_means).fillna(global_mean).to_numpy()
    )
    print(f"GlobalMean (Val-2024):   {val_global}")
    print(f"PerCropMean (Val-2024):  {val_per_crop}")

    candidates: list[tuple[str, dict[str, Any]]] = [("LinearRegression", {})]
    for depth in [16, None]:
        for msl in [2, 5]:
            candidates.append(
                (
                    "RandomForestRegressor",
                    {
                        "n_estimators": 200,
                        "max_depth": depth,
                        "min_samples_leaf": msl,
                        "random_state": 42,
                        "n_jobs": -1,
                    },
                )
            )
    for lr in [0.05, 0.1]:
        for md in [3, 5]:
            candidates.append(
                (
                    "GradientBoostingRegressor",
                    {
                        "n_estimators": 200,
                        "learning_rate": lr,
                        "max_depth": md,
                        "random_state": 42,
                    },
                )
            )

    best_entry: tuple[float, str, dict[str, Any], Pipeline, dict[str, float]] | None = None
    val_summary: list[dict[str, Any]] = []

    for model_name, params in candidates:
        pipe = Pipeline([("prep", make_preprocessor()), ("reg", build_estimator(model_name, params))])
        pipe.fit(train_df[FEATURES], train_df[TARGET])
        metrics_v = eval_metrics(val_df[TARGET], pipe.predict(val_df[FEATURES]))
        val_summary.append({"model": model_name, "params": params, **metrics_v})
        if model_name == "LinearRegression":
            print(f"LinearRegression (Val-2024): {metrics_v}")
        if best_entry is None or metrics_v["rmse"] < best_entry[0]:
            best_entry = (metrics_v["rmse"], model_name, params, pipe, metrics_v)

    assert best_entry is not None
    _, sel_name, sel_params, sel_pipe, sel_val_metrics = best_entry
    print(f"Selected on Val-2024: {sel_name} {sel_params} -> {sel_val_metrics}")

    # Canonical single held-out 2025 evaluation
    test_metrics = eval_metrics(test_df[TARGET], sel_pipe.predict(test_df[FEATURES]))
    print(f"Held-out Test-2025 ({sel_name}): {test_metrics}")

    # Refit selected configuration on 2021-2024 only (never 2025)
    refit_df = df[df["Anio"] <= 2024].copy()
    final_pipe = Pipeline([("prep", make_preprocessor()), ("reg", build_estimator(sel_name, sel_params))])
    final_pipe.fit(refit_df[FEATURES], refit_df[TARGET])

    with MODEL_PATH.open("wb") as f:
        pickle.dump(final_pipe, f, protocol=5)

    ohe: OneHotEncoder = final_pipe.named_steps["prep"].named_transformers_["cat"]
    known_categories = {col: [str(v) for v in cats] for col, cats in zip(CAT_COLS, ohe.categories_)}

    manifest_sha = sha256_file(MANIFEST_PATH) if MANIFEST_PATH.exists() else None
    metadata = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "data_path": str(DATA_PATH.relative_to(ROOT_DIR)),
        "data_sha256": sha256_file(DATA_PATH),
        "data_manifest_sha256": manifest_sha,
        "features": FEATURES,
        "target": TARGET,
        "target_unit": "tonnes per hectare",
        "primary_metric": "rmse",
        "selected_model": sel_name,
        "selected_params": sel_params,
        "train_years": [2021, 2022, 2023],
        "val_year": 2024,
        "test_year": 2025,
        "refit_years": [2021, 2022, 2023, 2024],
        "val_baselines": {"global_mean": val_global, "per_crop_mean": val_per_crop},
        "val_metrics": sel_val_metrics,
        "test_metrics": test_metrics,
        "known_categories": known_categories,
        "security_note": "model.bin is generated locally by train.py and must never be replaced with or loaded from an untrusted artifact.",
    }
    METADATA_PATH.write_text(json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Saved {MODEL_PATH} ({MODEL_PATH.stat().st_size / 1e6:.2f} MB) and {METADATA_PATH}")


if __name__ == "__main__":
    main()
