# Sonora Crop-Yield Estimator

Pre-harvest agricultural crop-yield estimator (`Rendimiento`, tonnes per hectare) for **Sonora, Mexico**, built for the **Machine Learning Zoomcamp 2026 Midterm Project** (Modules 1–6).

> **Informational Use Only**: Predictions are informational pre-harvest estimates based on historical DGSIAP/SIAP Sonora records, not a financial, insurance, or production guarantee.

## Problem Description & Use Case

- **Target users**: Agronomy planners, regional analysts, and agricultural researchers in Sonora.
- **Decision / use case**: Estimate expected crop yield (`tonnes/ha`) before planting/harvest given municipality (`Nommunicipio`), production cycle (`Nomcicloproductivo`), irrigation/rainfed modality (`Nommodalidad`), crop (`Nomcultivo`), and planned planted area (`Sembrada`, in hectares).
- **Evaluation metric**: **RMSE** (primary, penalizes large yield errors in tonnes/ha) with **MAE** as a supporting metric.

## Dataset & Provenance

- **Official source**: DGSIAP / SIAP *Cierre de la Producción Agrícola* municipal annual CSVs (2021–2025) from [Datos Abiertos Agrícola](https://nube.agricultura.gob.mx/datosAbiertos/Agricola.php) and official data dictionary (`Dicc 03 a 25`).
- **Filtering rules** (`prepare_data.py`):
  - `Nomestado == "Sonora"`
  - `Nomunidad == "Tonelada"` (excludes 4 `Manojo` rows)
  - `Rendimiento.notna()` (excludes 143 `Cosechada == 0` total-loss rows where `Rendimiento` is undefined)
- **Derived dataset**: [`data/sonora_crop_yield_2021_2025.csv`](data/sonora_crop_yield_2021_2025.csv) (**5,635** rows: `2021`: 952, `2022`: 1,190, `2023`: 1,321, `2024`: 1,127, `2025`: 1,045) with source URLs, checksums, and audit counts recorded in [`data_manifest.json`](data_manifest.json).
- **Excluded leakage / split columns**: `Volumenproduccion`, `Cosechada`, `Siniestrada`, `Preciomediorural`, `Valorproduccion`, and `Anio` (used strictly for temporal splitting).

## Modeling & Evaluation Design

- **Temporal split**:
  - Train: `2021–2023` (3,463 rows)
  - Validation (model selection & tuning): `2024` (1,127 rows)
  - Held-out final test (evaluated once in `train.py`): `2025` (1,045 rows)
- **Notebook vs. `train.py`**: [`notebook.ipynb`](notebook.ipynb) performs EDA, `Cosechada == 0` and high-yield `Pepino` outlier audits, feature importance inspection, and `2024` validation selection. [`train.py`](train.py) is the canonical single `2025` evaluation path and refits the validation-selected pipeline on **`2021–2024` only** (never `2025`) to produce `model.bin` and `model_metadata.json`.
- **Results** (`2024` Val / `2025` Test):
  - `GlobalMean` (Val-2024): RMSE `19.8199`, MAE `12.5974`
  - `PerCropMean` (Val-2024): RMSE `10.9703`, MAE `6.1305`
  - `LinearRegression` baseline (Val-2024): RMSE `9.9028`, MAE `5.6620`
  - **Selected**: `RandomForestRegressor(n_estimators=200, max_depth=None, min_samples_leaf=2)` → Val-2024 RMSE `8.4841` (MAE `3.6285`), Held-out Test-2025 RMSE `10.4956` (MAE `5.1430`).

> **Security Note**: `model.bin` is generated locally by `train.py` using `pickle` (`protocol=5`) and is excluded from Git. Never replace or load `model.bin` from an untrusted source.

## Environment Setup (`uv`)

This project uses [`uv`](https://docs.astral.sh/uv/) with [`pyproject.toml`](pyproject.toml) and [`uv.lock`](uv.lock) for reproducible Python 3.11 dependency management.

```bash
# 1. Install dependencies into .venv
uv sync --locked

# 2. Activate the virtual environment
source .venv/bin/activate
```

## Reproducing Data, Training & Tests

```bash
# Regenerate derived dataset & verify official SIAP checksums/schema
python prepare_data.py

# Train, run single 2025 held-out evaluation, and save model.bin + model_metadata.json
python train.py

# Run automated API tests
pytest tests/test_api.py -v
```

## Running the Prediction Service Locally

Start the FastAPI service (`predict.py`) with `uvicorn`:

```bash
uvicorn predict:app --host 0.0.0.0 --port 9696
```

Example request:

```bash
curl -X POST http://localhost:9696/predict \
  -H "Content-Type: application/json" \
  -d '{
    "Nommunicipio": "Hermosillo",
    "Nomcicloproductivo": "Otoño-Invierno",
    "Nommodalidad": "Riego",
    "Nomcultivo": "Trigo grano",
    "Sembrada": 1200.0
  }'
```

Example response:

```json
{
  "predicted_yield_ton_per_ha": 6.9381,
  "input_warnings": [],
  "note": "Informational pre-harvest estimate based on historical SIAP Sonora records; not a financial, insurance, or production guarantee."
}
```

- **Supported `Sembrada` range**: `Sembrada` must be greater than `0` and at most `42,000` hectares (the observed maximum in the 2021–2024 refit data; inputs above `42,000` ha are rejected with `422` rather than extrapolated).
- **Unseen categorical values**: `OneHotEncoder(handle_unknown="ignore")` encodes unseen `Nommunicipio`, `Nomcicloproductivo`, `Nommodalidad`, or `Nomcultivo` values as all-zero features and populates `input_warnings` in the response.

## Containerization (Docker)

Ensure `model.bin` and `model_metadata.json` have been generated locally via `python train.py` before building the image:

```bash
docker build -t sonora-crop-yield:latest .
docker run --rm -p 9696:9696 sonora-crop-yield:latest
```

Test the containerized service with the same `curl -X POST http://localhost:9696/predict` command above.

## Known Limitations & Cloud Deployment

- **Inter-annual variation**: `2025` Test RMSE (`10.4956`) is higher than `2024` Val RMSE (`8.4841`), consistent with year-to-year variation—including weather or drought effects—not represented in the pre-harvest SIAP inputs.
- **Cloud deployment**: Deferred until local Docker verification is complete; cloud deployment instructions and live endpoint/demo evidence will be added here before final submission.
