import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from predict import CropPlan, app

client = TestClient(app)


def test_predict_known_crop() -> None:
    payload = {
        "Nommunicipio": "Hermosillo",
        "Nomcicloproductivo": "Otoño-Invierno",
        "Nommodalidad": "Riego",
        "Nomcultivo": "Trigo grano",
        "Sembrada": 1200.0,
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["predicted_yield_ton_per_ha"] > 0
    assert body["input_warnings"] == []
    assert "Informational pre-harvest estimate" in body["note"]


def test_predict_unseen_category_warns() -> None:
    payload = {
        "Nommunicipio": "MunicipioDesconocido",
        "Nomcicloproductivo": "Otoño-Invierno",
        "Nommodalidad": "Riego",
        "Nomcultivo": "Trigo grano",
        "Sembrada": 50.0,
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["predicted_yield_ton_per_ha"] >= 0
    assert len(body["input_warnings"]) == 1
    assert "Nommunicipio" in body["input_warnings"][0]


def test_predict_rejects_non_positive_sembrada() -> None:
    payload = {
        "Nommunicipio": "Hermosillo",
        "Nomcicloproductivo": "Otoño-Invierno",
        "Nommodalidad": "Riego",
        "Nomcultivo": "Trigo grano",
        "Sembrada": 0.0,
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 422


def test_predict_rejects_whitespace_only_category() -> None:
    payload = {
        "Nommunicipio": "   ",
        "Nomcicloproductivo": "Otoño-Invierno",
        "Nommodalidad": "Riego",
        "Nomcultivo": "Trigo grano",
        "Sembrada": 50.0,
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 422


def test_predict_rejects_overly_long_category() -> None:
    payload = {
        "Nommunicipio": "x" * 101,
        "Nomcicloproductivo": "Otoño-Invierno",
        "Nommodalidad": "Riego",
        "Nomcultivo": "Trigo grano",
        "Sembrada": 50.0,
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 422


def test_predict_rejects_sembrada_above_bound() -> None:
    payload = {
        "Nommunicipio": "Hermosillo",
        "Nomcicloproductivo": "Otoño-Invierno",
        "Nommodalidad": "Riego",
        "Nomcultivo": "Trigo grano",
        "Sembrada": 42_001.0,
    }
    resp = client.post("/predict", json=payload)
    assert resp.status_code == 422


def test_crop_plan_rejects_non_finite_sembrada() -> None:
    with pytest.raises(ValidationError):
        CropPlan(
            Nommunicipio="Hermosillo",
            Nomcicloproductivo="Otoño-Invierno",
            Nommodalidad="Riego",
            Nomcultivo="Trigo grano",
            Sembrada=float("inf"),
        )


def test_predict_rejects_non_finite_json_sembrada() -> None:
    raw_json = (
        '{"Nommunicipio":"Hermosillo","Nomcicloproductivo":"Otoño-Invierno",'
        '"Nommodalidad":"Riego","Nomcultivo":"Trigo grano","Sembrada":Infinity}'
    )
    resp = client.post("/predict", content=raw_json, headers={"Content-Type": "application/json"})
    assert resp.status_code in (400, 422)
