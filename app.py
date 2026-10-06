import os
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE, "data", "flood_risk_binary_classification.csv")
FEATURES = ["rainfall_mm", "river_level_m", "elevation_m", "soil_moisture_percent",
            "temperature_c", "humidity_percent", "drainage_capacity_percent"]
TARGET = "flood_risk"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
S = {}


def synth(n=500, seed=42):
    r = np.random.default_rng(seed)
    rain = np.clip(r.gamma(2.2, 60, n), 0, 500)
    elev = np.clip(r.gamma(2.2, 70, n), 0, 500)
    river = np.clip(r.normal(3.5, 1.6, n) + rain / 110 - elev / 400, 0, 15)
    soil = np.clip(r.normal(40, 14, n) + rain / 14, 0, 100)
    temp = np.clip(r.normal(28, 6, n), 0, 45)
    hum = np.clip(r.normal(55, 14, n) + rain / 20, 0, 100)
    drain = np.clip(r.normal(60, 20, n), 0, 100)
    z = (0.02 * (rain - 150) + 0.6 * (river - 4.5) - 0.012 * (elev - 150) + 0.04 * (soil - 50)
         + 0.02 * (hum - 60) - 0.04 * (drain - 55) - 0.01 * (temp - 28) + r.normal(0, 1.0, n))
    df = pd.DataFrame(dict(zip(FEATURES, [rain, river, elev, soil, temp, hum, drain])))
    df[TARGET] = (z > 0.4).astype(int)
    return df.round(2)


def train(df, name):
    X, y = df[FEATURES], df[TARGET].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    S.update(
        model=pipe, df=df, name=name,
        acc=round(accuracy_score(yte, pred) * 100, 1),
        cm=confusion_matrix(yte, pred, labels=[0, 1]).tolist(),
        imp=[{"feature": f, "value": round(float(c), 3)} for f, c in zip(FEATURES, pipe[-1].coef_[0])],
        dist=[int((y == 0).sum()), int((y == 1).sum())],
    )


def boot():
    if not os.path.exists(CSV):
        os.makedirs(os.path.dirname(CSV), exist_ok=True)
        synth().to_csv(CSV, index=False)
    train(pd.read_csv(CSV), os.path.basename(CSV))


boot()


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    df = S["df"]
    return jsonify(status="Ready", filename=S["name"], accuracy=S["acc"], rows=len(df),
                   columns=df.shape[1], features=len(FEATURES), confusion=S["cm"],
                   distribution=S["dist"], importance=S["imp"])


@app.post("/api/predict")
def predict():
    data = request.get_json(silent=True) or {}
    row = {}
    for f in FEATURES:
        try:
            v = float(data[f])
            assert np.isfinite(v)
            row[f] = v
        except Exception:
            return jsonify(error=f"Please enter a valid value for {f}.", field=f), 400
    p = float(S["model"].predict_proba(pd.DataFrame([row], columns=FEATURES))[0][1])
    flood = int(p >= 0.5)
    return jsonify(
        prediction=flood, label="FLOOD RISK" if flood else "LOW RISK", probability=round(p * 100, 1),
        message="The model indicates a higher flood-risk condition." if flood
        else "The model indicates a lower flood-risk condition.")


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".csv"):
        return jsonify(error="Please upload a .csv file."), 400
    try:
        df = pd.read_csv(f)
    except Exception:
        return jsonify(error="Could not read the CSV file."), 400
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        return jsonify(error="Dataset validation failed.", missing=missing), 400
    df = df[FEATURES + [TARGET]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(df) < 20 or set(df[TARGET].unique()) - {0, 1} or df[TARGET].nunique() < 2:
        return jsonify(error="Need 20+ valid rows and a flood_risk column containing both 0 and 1."), 400
    df[TARGET] = df[TARGET].astype(int)
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    df.to_csv(CSV, index=False)
    train(df, os.path.basename(CSV))
    return jsonify(ok=True, accuracy=S["acc"], rows=len(df))


@app.get("/api/preview")
def preview():
    df = S["df"].head(8).round(2)
    return jsonify(columns=list(df.columns), rows=df.values.tolist())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
import os
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE, "data", "flood_risk_binary_classification.csv")
FEATURES = ["rainfall_mm", "river_level_m", "elevation_m", "soil_moisture_percent",
            "temperature_c", "humidity_percent", "drainage_capacity_percent"]
TARGET = "flood_risk"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
S = {}


def synth(n=500, seed=42):
    r = np.random.default_rng(seed)
    rain = np.clip(r.gamma(2.2, 60, n), 0, 500)
    elev = np.clip(r.gamma(2.2, 70, n), 0, 500)
    river = np.clip(r.normal(3.5, 1.6, n) + rain / 110 - elev / 400, 0, 15)
    soil = np.clip(r.normal(40, 14, n) + rain / 14, 0, 100)
    temp = np.clip(r.normal(28, 6, n), 0, 45)
    hum = np.clip(r.normal(55, 14, n) + rain / 20, 0, 100)
    drain = np.clip(r.normal(60, 20, n), 0, 100)
    z = (0.02 * (rain - 150) + 0.6 * (river - 4.5) - 0.012 * (elev - 150) + 0.04 * (soil - 50)
         + 0.02 * (hum - 60) - 0.04 * (drain - 55) - 0.01 * (temp - 28) + r.normal(0, 1.0, n))
    df = pd.DataFrame(dict(zip(FEATURES, [rain, river, elev, soil, temp, hum, drain])))
    df[TARGET] = (z > 0.4).astype(int)
    return df.round(2)


def train(df, name):
    X, y = df[FEATURES], df[TARGET].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    S.update(
        model=pipe, df=df, name=name,
        acc=round(accuracy_score(yte, pred) * 100, 1),
        cm=confusion_matrix(yte, pred, labels=[0, 1]).tolist(),
        imp=[{"feature": f, "value": round(float(c), 3)} for f, c in zip(FEATURES, pipe[-1].coef_[0])],
        dist=[int((y == 0).sum()), int((y == 1).sum())],
    )


def boot():
    if not os.path.exists(CSV):
        os.makedirs(os.path.dirname(CSV), exist_ok=True)
        synth().to_csv(CSV, index=False)
    train(pd.read_csv(CSV), os.path.basename(CSV))


boot()


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    df = S["df"]
    return jsonify(status="Ready", filename=S["name"], accuracy=S["acc"], rows=len(df),
                   columns=df.shape[1], features=len(FEATURES), confusion=S["cm"],
                   distribution=S["dist"], importance=S["imp"])


@app.post("/api/predict")
def predict():
    data = request.get_json(silent=True) or {}
    row = {}
    for f in FEATURES:
        try:
            v = float(data[f])
            assert np.isfinite(v)
            row[f] = v
        except Exception:
            return jsonify(error=f"Please enter a valid value for {f}.", field=f), 400
    p = float(S["model"].predict_proba(pd.DataFrame([row], columns=FEATURES))[0][1])
    flood = int(p >= 0.5)
    return jsonify(
        prediction=flood, label="FLOOD RISK" if flood else "LOW RISK", probability=round(p * 100, 1),
        message="The model indicates a higher flood-risk condition." if flood
        else "The model indicates a lower flood-risk condition.")


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".csv"):
        return jsonify(error="Please upload a .csv file."), 400
    try:
        df = pd.read_csv(f)
    except Exception:
        return jsonify(error="Could not read the CSV file."), 400
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        return jsonify(error="Dataset validation failed.", missing=missing), 400
    df = df[FEATURES + [TARGET]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(df) < 20 or set(df[TARGET].unique()) - {0, 1} or df[TARGET].nunique() < 2:
        return jsonify(error="Need 20+ valid rows and a flood_risk column containing both 0 and 1."), 400
    df[TARGET] = df[TARGET].astype(int)
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    df.to_csv(CSV, index=False)
    train(df, os.path.basename(CSV))
    return jsonify(ok=True, accuracy=S["acc"], rows=len(df))


@app.get("/api/preview")
def preview():
    df = S["df"].head(8).round(2)
    return jsonify(columns=list(df.columns), rows=df.values.tolist())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
import os
import numpy as np
import pandas as pd
from flask import Flask, jsonify, render_template, request
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

BASE = os.path.dirname(os.path.abspath(__file__))
CSV = os.path.join(BASE, "data", "flood_risk_binary_classification.csv")
FEATURES = ["rainfall_mm", "river_level_m", "elevation_m", "soil_moisture_percent",
            "temperature_c", "humidity_percent", "drainage_capacity_percent"]
TARGET = "flood_risk"

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
S = {}


def synth(n=500, seed=42):
    r = np.random.default_rng(seed)
    rain = np.clip(r.gamma(2.2, 60, n), 0, 500)
    elev = np.clip(r.gamma(2.2, 70, n), 0, 500)
    river = np.clip(r.normal(3.5, 1.6, n) + rain / 110 - elev / 400, 0, 15)
    soil = np.clip(r.normal(40, 14, n) + rain / 14, 0, 100)
    temp = np.clip(r.normal(28, 6, n), 0, 45)
    hum = np.clip(r.normal(55, 14, n) + rain / 20, 0, 100)
    drain = np.clip(r.normal(60, 20, n), 0, 100)
    z = (0.02 * (rain - 150) + 0.6 * (river - 4.5) - 0.012 * (elev - 150) + 0.04 * (soil - 50)
         + 0.02 * (hum - 60) - 0.04 * (drain - 55) - 0.01 * (temp - 28) + r.normal(0, 1.0, n))
    df = pd.DataFrame(dict(zip(FEATURES, [rain, river, elev, soil, temp, hum, drain])))
    df[TARGET] = (z > 0.4).astype(int)
    return df.round(2)


def train(df, name):
    X, y = df[FEATURES], df[TARGET].astype(int)
    Xtr, Xte, ytr, yte = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    pipe = make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000)).fit(Xtr, ytr)
    pred = pipe.predict(Xte)
    S.update(
        model=pipe, df=df, name=name,
        acc=round(accuracy_score(yte, pred) * 100, 1),
        cm=confusion_matrix(yte, pred, labels=[0, 1]).tolist(),
        imp=[{"feature": f, "value": round(float(c), 3)} for f, c in zip(FEATURES, pipe[-1].coef_[0])],
        dist=[int((y == 0).sum()), int((y == 1).sum())],
    )


def boot():
    if not os.path.exists(CSV):
        os.makedirs(os.path.dirname(CSV), exist_ok=True)
        synth().to_csv(CSV, index=False)
    train(pd.read_csv(CSV), os.path.basename(CSV))


boot()


@app.route("/")
def index():
    return render_template("index.html")


@app.get("/api/status")
def status():
    df = S["df"]
    return jsonify(status="Ready", filename=S["name"], accuracy=S["acc"], rows=len(df),
                   columns=df.shape[1], features=len(FEATURES), confusion=S["cm"],
                   distribution=S["dist"], importance=S["imp"])


@app.post("/api/predict")
def predict():
    data = request.get_json(silent=True) or {}
    row = {}
    for f in FEATURES:
        try:
            v = float(data[f])
            assert np.isfinite(v)
            row[f] = v
        except Exception:
            return jsonify(error=f"Please enter a valid value for {f}.", field=f), 400
    p = float(S["model"].predict_proba(pd.DataFrame([row], columns=FEATURES))[0][1])
    flood = int(p >= 0.5)
    return jsonify(
        prediction=flood, label="FLOOD RISK" if flood else "LOW RISK", probability=round(p * 100, 1),
        message="The model indicates a higher flood-risk condition." if flood
        else "The model indicates a lower flood-risk condition.")


@app.post("/api/upload")
def upload():
    f = request.files.get("file")
    if not f or not f.filename.lower().endswith(".csv"):
        return jsonify(error="Please upload a .csv file."), 400
    try:
        df = pd.read_csv(f)
    except Exception:
        return jsonify(error="Could not read the CSV file."), 400
    missing = [c for c in FEATURES + [TARGET] if c not in df.columns]
    if missing:
        return jsonify(error="Dataset validation failed.", missing=missing), 400
    df = df[FEATURES + [TARGET]].apply(pd.to_numeric, errors="coerce").dropna()
    if len(df) < 20 or set(df[TARGET].unique()) - {0, 1} or df[TARGET].nunique() < 2:
        return jsonify(error="Need 20+ valid rows and a flood_risk column containing both 0 and 1."), 400
    df[TARGET] = df[TARGET].astype(int)
    os.makedirs(os.path.dirname(CSV), exist_ok=True)
    df.to_csv(CSV, index=False)
    train(df, os.path.basename(CSV))
    return jsonify(ok=True, accuracy=S["acc"], rows=len(df))


@app.get("/api/preview")
def preview():
    df = S["df"].head(8).round(2)
    return jsonify(columns=list(df.columns), rows=df.values.tolist())


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
