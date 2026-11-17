from __future__ import annotations

import hashlib
import json
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent
RAW_DIR = ROOT_DIR / "data" / "raw"
DERIVED_PATH = ROOT_DIR / "data" / "sonora_crop_yield_2021_2025.csv"
MANIFEST_PATH = ROOT_DIR / "data_manifest.json"

SIAP_PORTAL_URL = "https://www.gob.mx/siap/acciones-y-programas/datos-abiertos-informacion-agricola"
SIAP_AGRICOLA_URL = "https://nube.agricultura.gob.mx/datosAbiertos/Agricola.php"
SIAP_DICTIONARY_URL = (
    "https://nube.agricultura.gob.mx/index.php?view=5D24F995-E734D711-1EA6F8D2-9D1387D7"
)
SIAP_CSV_URL_TEMPLATE = (
    "https://nube.agricultura.gob.mx/index.php?view=10AE434F-A2158368-A120BC5A-EDF4AFAA&ANIO={year}"
)

YEARS = [2021, 2022, 2023, 2024, 2025]
EXPECTED_RAW_COLUMNS = [
    "Anio",
    "Idestado",
    "Nomestado",
    "Idmunicipio",
    "Nommunicipio",
    "Idciclo",
    "Nomcicloproductivo",
    "Idmodalidad",
    "Nommodalidad",
    "Idunidadmedida",
    "Nomunidad",
    "Idcultivo",
    "Nomcultivo",
    "Sembrada",
    "Cosechada",
    "Siniestrada",
    "Volumenproduccion",
    "Rendimiento",
    "Preciomediorural",
    "Valorproduccion",
]
KEEP_COLUMNS = [
    "Anio",
    "Nommunicipio",
    "Nomcicloproductivo",
    "Nommodalidad",
    "Nomcultivo",
    "Sembrada",
    "Rendimiento",
]
EXPECTED_YEAR_COUNTS = {
    2021: 952,
    2022: 1190,
    2023: 1321,
    2024: 1127,
    2025: 1045,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def download_if_missing(url: str, dest: Path) -> None:
    if dest.exists() and dest.stat().st_size > 0:
        return
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as resp, dest.open("wb") as out:
        if resp.status != 200:
            raise RuntimeError(f"Unexpected HTTP {resp.status} for {url}")
        out.write(resp.read())


def main() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    source_records: list[dict[str, str | int]] = []
    frames: list[pd.DataFrame] = []
    audit_counts = {"sonora_total": 0, "dropped_non_tonelada": 0, "dropped_nan_rendimiento": 0}

    for year in YEARS:
        url = SIAP_CSV_URL_TEMPLATE.format(year=year)
        raw_path = RAW_DIR / f"cierre_{year}.csv"
        download_if_missing(url, raw_path)
        source_records.append(
            {
                "year": year,
                "url": url,
                "filename": raw_path.name,
                "size_bytes": raw_path.stat().st_size,
                "sha256": sha256_file(raw_path),
            }
        )

        df = pd.read_csv(raw_path, encoding="latin1", low_memory=False)
        missing_cols = [c for c in EXPECTED_RAW_COLUMNS if c not in df.columns]
        if missing_cols:
            raise ValueError(f"Schema drift in {raw_path.name}: missing columns {missing_cols}")

        son = df[df["Nomestado"].astype(str).str.strip().str.upper() == "SONORA"].copy()
        audit_counts["sonora_total"] += len(son)

        ton = son[son["Nomunidad"].astype(str).str.strip() == "Tonelada"].copy()
        audit_counts["dropped_non_tonelada"] += len(son) - len(ton)

        # Cosechada == 0 (total crop loss) yields undefined Rendimiento (NaN)
        nan_mask = ton["Rendimiento"].isna()
        if nan_mask.any():
            non_zero_harvest_nan = ton.loc[nan_mask & (pd.to_numeric(ton["Cosechada"], errors="coerce") != 0)]
            if not non_zero_harvest_nan.empty:
                raise ValueError(f"Unexpected NaN Rendimiento with Cosechada != 0 in {year}")
        audit_counts["dropped_nan_rendimiento"] += int(nan_mask.sum())

        clean = ton.loc[~nan_mask, KEEP_COLUMNS].copy()
        frames.append(clean)

    derived = pd.concat(frames, ignore_index=True)
    derived["Anio"] = pd.to_numeric(derived["Anio"], errors="raise").astype(int)
    derived["Sembrada"] = pd.to_numeric(derived["Sembrada"], errors="raise").astype(float)
    derived["Rendimiento"] = pd.to_numeric(derived["Rendimiento"], errors="raise").astype(float)
    for col in ["Nommunicipio", "Nomcicloproductivo", "Nommodalidad", "Nomcultivo"]:
        derived[col] = derived[col].astype(str).str.strip()

    # Loud data-quality assertions
    if derived.isna().any().any():
        raise ValueError(f"Derived dataset contains unexpected NaNs:\n{derived.isna().sum()}")
    if (derived["Sembrada"] <= 0).any():
        raise ValueError("Found non-positive Sembrada values in derived dataset")
    if (derived["Rendimiento"] < 0).any():
        raise ValueError("Found negative Rendimiento values in derived dataset")

    actual_counts = {int(k): int(v) for k, v in derived["Anio"].value_counts().sort_index().items()}
    if actual_counts != EXPECTED_YEAR_COUNTS:
        raise ValueError(f"Row count mismatch: expected {EXPECTED_YEAR_COUNTS}, got {actual_counts}")

    DERIVED_PATH.parent.mkdir(parents=True, exist_ok=True)
    derived.to_csv(DERIVED_PATH, index=False)

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "portal_url": SIAP_PORTAL_URL,
        "agricola_page_url": SIAP_AGRICOLA_URL,
        "dictionary_url": SIAP_DICTIONARY_URL,
        "filtering_rules": {
            "Nomestado": "Sonora",
            "Nomunidad": "Tonelada",
            "Rendimiento": "notna() (excludes Cosechada == 0 undefined yield)",
        },
        "audit_counts": audit_counts,
        "expected_year_counts": EXPECTED_YEAR_COUNTS,
        "actual_year_counts": actual_counts,
        "derived_dataset": {
            "path": str(DERIVED_PATH.relative_to(ROOT_DIR)),
            "rows": len(derived),
            "columns": list(derived.columns),
            "sha256": sha256_file(DERIVED_PATH),
        },
        "sources": source_records,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {DERIVED_PATH} ({len(derived)} rows) and {MANIFEST_PATH}")
    print("Audit counts:", audit_counts)


if __name__ == "__main__":
    main()
