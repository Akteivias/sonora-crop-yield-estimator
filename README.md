# Sonora Crop-Yield Estimator

Pre-harvest agricultural crop-yield estimator (`Rendimiento`, tonnes per hectare) for **Sonora, Mexico**, built for the **Machine Learning Zoomcamp 2026 Midterm Project** (Modules 1–6).

> **Informational Use Only**: Predictions are informational pre-harvest estimates based on historical DGSIAP/SIAP Sonora records, not a financial, insurance, or production guarantee.

## Problem Description & Use Case

- **Target users**: Agronomy planners, regional analysts, and agricultural researchers in Sonora.
- **Decision / use case**: Estimate expected crop yield (`tonnes/ha`) before planting/harvest given municipality (`Nommunicipio`), production cycle (`Nomcicloproductivo`), irrigation/rainfed modality (`Nommodalidad`), crop (`Nomcultivo`), and planned planted area (`Sembrada`, in hectares).
- **Evaluation metric**: **RMSE** (primary, penalizes large yield errors in tonnes/ha) with **MAE** as a supporting metric.

## Dataset & Provenance

- **Source**: DGSIAP / SIAP *Cierre de la Producción Agrícola* municipal annual CSVs (2021–2025) from [Datos Abiertos Agrícola](https://nube.agricultura.gob.mx/datosAbiertos/Agricola.php).
- **Reproducible data**: the committed derived dataset, [`data/sonora_crop_yield_2021_2025.csv`](data/sonora_crop_yield_2021_2025.csv), has 5,635 Sonora records. [`prepare_data.py`](prepare_data.py) applies the preparation rules; [`data_manifest.json`](data_manifest.json) records source URLs and checksums.
- Only pre-harvest features are used; post-harvest production and value columns are excluded to prevent leakage.

## Modeling & Evaluation Design

- **Temporal split**: train `2021–2023`, tune/select on `2024`, and evaluate once on the held-out `2025` test set.
- [`notebook.ipynb`](notebook.ipynb) contains data preparation, EDA, outlier and feature-importance analysis, and validation-based model selection. [`train.py`](train.py) refits the selected pipeline on `2021–2024` and writes `model.bin` and `model_metadata.json`.
- **Models**: a `LinearRegression` baseline plus tuned `RandomForestRegressor` and `GradientBoostingRegressor` candidates. The selected random forest (`n_estimators=200`, `max_depth=None`, `min_samples_leaf=2`) achieved validation RMSE/MAE `8.4841` / `3.6285` and held-out test RMSE/MAE `10.4956` / `5.1430`.

## Environment Setup (`uv`)

This project uses [`uv`](https://docs.astral.sh/uv/) with [`pyproject.toml`](pyproject.toml) and [`uv.lock`](uv.lock) for reproducible Python 3.11 dependency management.

```bash
uv sync --locked
source .venv/bin/activate
```

## Reproducing Data, Training & Tests

```bash
python prepare_data.py
python train.py
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

- `Sembrada` must be greater than `0` and at most `42,000` hectares; invalid requests return `422`.

## Containerization (Docker)

The image trains the model from the committed derived data during the build:

```bash
docker build -t sonora-crop-yield:latest .
docker run --rm -p 9696:9696 sonora-crop-yield:latest
```

Test the containerized service with the same `curl -X POST http://localhost:9696/predict` command above.

## Known Limitations

- **Inter-annual variation**: `2025` Test RMSE (`10.4956`) is higher than `2024` Val RMSE (`8.4841`), consistent with year-to-year variation—including weather or drought effects—not represented in the pre-harvest SIAP inputs.

## Cloud Deployment (Render)

- [`render.yaml`](render.yaml) defines the public Docker web service; its image trains the model during the build from the committed derived data and manifest.
- **Public Base URL**: <https://sonora-crop-yield-estimator-cd8z.onrender.com>
- **Interactive API Docs**: [OpenAPI / Swagger UI](https://sonora-crop-yield-estimator-cd8z.onrender.com/docs)
- **Prediction Endpoint**: `POST https://sonora-crop-yield-estimator-cd8z.onrender.com/predict`

> **Note**: Render Free services spin down after 15 minutes of inactivity and may take about a minute to wake on the first request.

Verified live request:

```bash
curl -sS -w "\nHTTP:%{http_code}\n" \
  -X POST https://sonora-crop-yield-estimator-cd8z.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{"Nommunicipio":"Hermosillo","Nomcicloproductivo":"Otoño-Invierno","Nommodalidad":"Riego","Nomcultivo":"Trigo grano","Sembrada":1200.0}'
```

The recorded request returned `HTTP:200`.

Live terminal demo:

![Live Render API prediction demo](docs/evidence/render-live-demo.gif)
