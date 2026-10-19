"""Tests unitaires sans base de données : lancer avec `pytest -q` dans backend/."""
import os
from datetime import datetime, timezone

import pytest

os.environ["ENABLE_BACKGROUND"] = "false"

from pydantic import ValidationError  # noqa: E402

from app.schemas import SensorReading, ThresholdUpdate  # noqa: E402
from app.services.anomaly import isolation_forest_scores, zscore  # noqa: E402
from app.services.collectors import aqi_to_concentration  # noqa: E402
from app.services.recommendations import for_pm25  # noqa: E402
from ml.synthetic import generate  # noqa: E402
from ml.train import train  # noqa: E402


def test_aqi_conversion():
    assert aqi_to_concentration("pm25", 50) == 12.0
    assert aqi_to_concentration("pm25", 100) == 35.4
    assert 12 < aqi_to_concentration("pm25", 75) < 35.4


def test_zscore_detects_spike():
    history = [15, 16, 14, 15, 17, 16, 15, 14, 16, 15]
    assert zscore(600, history)[0] is True
    assert zscore(16, history)[0] is False
    assert zscore(800, [])[0] is True        # capteur neuf : la règle de plausibilité suffit
    assert zscore(40, [])[0] is False


def test_isolation_forest_flags_outlier():
    import pandas as pd
    df = pd.DataFrame({"pm25": [15] * 99 + [800], "temperature": [12] * 100, "humidity": [70] * 100})
    df.iloc[:99] = df.iloc[:99] + pd.DataFrame(
        {"pm25": range(99), "temperature": range(99), "humidity": range(99)}).mod(3)
    scores = isolation_forest_scores(df)
    assert scores[-1] > 0.7


def test_recommendation_levels():
    assert for_pm25(5)["level"] == "bon"
    assert for_pm25(60)["level"] == "mauvais"


def test_sensor_validation_rejects_bad_input():
    ok = SensorReading(sensor_id="iot-01", timestamp=datetime.now(timezone.utc), pm25=12, temperature=10, humidity=50)
    assert ok.pm25 == 12
    with pytest.raises(ValidationError):
        SensorReading(sensor_id="DROP TABLE", timestamp=datetime.now(timezone.utc), pm25=12, temperature=10, humidity=50)
    with pytest.raises(ValidationError):
        ThresholdUpdate(pollutant="pm25", value=-5)


def test_model_beats_70_percent(tmp_path):
    csv = tmp_path / "h.csv"
    generate(180).to_csv(csv, index=False)
    meta = train(str(csv), str(tmp_path))
    best = meta["metrics"][meta["best_model"]]
    assert best["precision"] > 70
    assert (tmp_path / "pm25_model.joblib").exists()


def test_traffic_profile_rush_hour_and_night():
    from datetime import datetime
    from app.services.mobility import level, traffic_profile
    rush, _ = traffic_profile(datetime(2026, 10, 20, 8, 0))     # mardi 8 h
    night, _ = traffic_profile(datetime(2026, 10, 20, 3, 0))    # mardi 3 h
    assert rush > night + 20
    assert level(85) == "saturé" and level(20) == "fluide"


def test_model_works_with_and_without_traffic(tmp_path):
    import pandas as pd
    df = generate(120)
    df.to_csv(tmp_path / "with.csv", index=False)
    df.drop(columns=["traffic_index"]).to_csv(tmp_path / "without.csv", index=False)
    assert train(str(tmp_path / "with.csv"), str(tmp_path))["uses_traffic"] is True
    assert train(str(tmp_path / "without.csv"), str(tmp_path))["uses_traffic"] is False
