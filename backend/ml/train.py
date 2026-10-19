"""Entraînement et évaluation du modèle de prédiction PM2.5 à J+1.

Démarche (c'est ce qu'il faut expliquer au jury) :
1. Données : base de données si >= 90 jours, sinon le CSV historique.
2. Découpage TEMPOREL : les 30 derniers jours servent de test (critère du client :
   "précision > 70 % sur 30 jours de test"). On ne mélange jamais passé et futur,
   sinon le modèle "voit" l'avenir et les scores sont faux.
3. Baseline naïve : "demain = aujourd'hui". Un modèle qui ne bat pas ça ne sert à rien.
4. Phase 1 : régression linéaire multiple (standardisée).
5. Phase 2 : Random Forest.
6. Métriques : RMSE (erreur en µg/m³), MAPE (erreur en %), précision = 100 - MAPE,
   et exactitude de la classe d'alerte (bon / moyen / dégradé / mauvais).
7. On garde le meilleur modèle (RMSE la plus basse) + ses métriques en JSON.

Usage : python -m ml.train [--csv data/historique.csv]
"""
import argparse
import json
import os
from datetime import datetime, timezone

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

from .features import to_daily, training_set

TEST_DAYS = 30
CLASS_BINS = [0, 10, 25, 50, np.inf]          # seuils PM2.5 journaliers (µg/m³)
CLASS_LABELS = ["bon", "moyen", "dégradé", "mauvais"]


def load_history(csv_path: str | None) -> pd.DataFrame:
    if csv_path is None:
        try:
            from app.services.repository import hourly_history
            df = hourly_history(days=400)
            if df["time"].nunique() >= 90 * 24:
                print("Données chargées depuis la base")
                return df
        except Exception as exc:  # base indisponible -> CSV
            print(f"Base indisponible ({exc}), on utilise le CSV")
        csv_path = os.path.join(os.getenv("DATA_DIR", "data"), "historique.csv")
    if not os.path.exists(csv_path):
        from .synthetic import generate
        print("Pas de CSV : génération de 180 jours synthétiques")
        df = generate(180)
        df.to_csv(csv_path, index=False)
    return pd.read_csv(csv_path)


def evaluate(y_true, y_pred) -> dict:
    mape = mean_absolute_percentage_error(y_true, y_pred)
    true_cls = pd.cut(y_true, CLASS_BINS, labels=CLASS_LABELS)
    pred_cls = pd.cut(y_pred, CLASS_BINS, labels=CLASS_LABELS)
    return {
        "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 2),
        "mape": round(float(mape) * 100, 1),
        "precision": round(float(1 - mape) * 100, 1),
        "class_accuracy": round(float((np.asarray(true_cls) == np.asarray(pred_cls)).mean()) * 100, 1),
    }


def train(csv_path: str | None = None, model_dir: str | None = None) -> dict:
    model_dir = model_dir or os.getenv("MODEL_DIR", "models")
    os.makedirs(model_dir, exist_ok=True)
    daily = to_daily(load_history(csv_path))
    X, y = training_set(daily)
    X_train, X_test = X.iloc[:-TEST_DAYS], X.iloc[-TEST_DAYS:]
    y_train, y_test = y.iloc[:-TEST_DAYS], y.iloc[-TEST_DAYS:]

    results = {"baseline_persistence": evaluate(y_test, X_test["lag_1"].to_numpy())}
    candidates = {
        "linear_regression": make_pipeline(StandardScaler(), LinearRegression()),
        "random_forest": RandomForestRegressor(n_estimators=300, max_depth=10, min_samples_leaf=2,
                                               random_state=42, n_jobs=-1),
    }
    fitted = {}
    for name, model in candidates.items():
        model.fit(X_train, y_train)
        results[name] = evaluate(y_test, model.predict(X_test))
        fitted[name] = model

    best = min(fitted, key=lambda n: results[n]["rmse"])
    # Erreur résiduelle sur le test -> sert à construire l'intervalle de confiance
    residual_std = float(np.std(y_test - fitted[best].predict(X_test)))
    # On ré-entraîne le meilleur modèle sur TOUT l'historique pour la production
    final = fitted[best].fit(X, y)

    importances = None
    if best == "random_forest":
        importances = dict(sorted(zip(X.columns, final.feature_importances_.round(3).tolist()),
                                  key=lambda kv: -kv[1]))
    meta = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "best_model": best,
        "train_days": len(X_train),
        "test_days": TEST_DAYS,
        "metrics": results,
        "residual_std": round(residual_std, 2),
        "feature_importances": importances,
        "features": list(X.columns),
        "uses_traffic": "fc_traffic" in X.columns,
    }
    joblib.dump(final, os.path.join(model_dir, "pm25_model.joblib"))
    with open(os.path.join(model_dir, "metrics.json"), "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)
    return meta


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--csv", default=None)
    p.add_argument("--model-dir", default=None)
    a = p.parse_args()
    print(json.dumps(train(a.csv, a.model_dir), indent=2, ensure_ascii=False))
