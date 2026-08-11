# Anomalock

ML-based login risk & anomaly detection system — a lightweight version of the risk-based authentication (RBA)
engines used by Okta, Microsoft Entra, and Auth0. Scores each login attempt on behavioral signals (impossible
travel, brute-force patterns, new-device/off-hours logins) and flags high-risk attempts for step-up
verification instead of either annoying every user or missing slow, low-volume attacks.

## Status

**Phase 4 (dashboard) — done.** React + Socket.IO live login feed, plus a mock login form with three
scenario presets (normal / new device / impossible travel) that shows the model's score turning into an
actual step-up-authentication prompt. See [Running the dashboard](#running-the-dashboard) below.

**Phase 3 (API) — done.** FastAPI scoring service + replay tool. Verified end-to-end against a real attack
sequence in the dataset: an account-takeover login scored 99.2/100 (flagged for unusual login time + new
device/network), and the attacker's follow-up logins scored 99.2-99.5 on `impossible_travel`. See
[Running the API](#running-the-api) below.

**Phase 2 (feature engineering & modeling) — done.** See [`reports/model_comparison.md`](reports/model_comparison.md)
for the full writeup. Headline, honestly reported: none of the three models is production-ready yet — the
rule-based baseline gets 81.6% recall but flags 29% of all traffic, and Isolation Forest (unsupervised)
outperforms the supervised Random Forest at every review-budget level, largely because there are only 141
labeled attacks to learn from. The live API (below) serves Isolation Forest as the primary score, with the
baseline rules surfaced as human-readable "flagged reasons" alongside it. Phase 1 data/EDA writeup:
[`data/DATA.md`](data/DATA.md), [`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb).

### Model comparison (test set, 137,164 rows / 38 labeled attacks)

| Model | Precision | Recall | False positive rate |
|---|---|---|---|
| Baseline (rules) | 0.08% | 81.6% | 28.8% |
| Isolation Forest | 0.0% | 0.0% | 0.11% |
| Random Forest | 0.03% | 21.1% | 19.0% |

| Recall @ review budget | 1% | 5% | 20% |
|---|---|---|---|
| Isolation Forest | 7.9% | 28.9% | 60.5% |
| Random Forest | 0.0% | 0.0% | 21.1% |

## Project structure

```
data/                  raw + processed data, not committed except small samples/docs
notebooks/             exploratory analysis
src/anomalock/
  ingest/               data download/subsampling
  features/             behavioral feature engineering (Phase 2)
  models/                baseline, Isolation Forest, Random Forest (Phase 2)
api/                    FastAPI scoring service (Phase 3)
dashboard/              React + Socket.IO live dashboard (Phase 4)
reports/                model comparison / results writeups
```

## Data

Real-world [RBA Dataset](https://zenodo.org/record/6782156) (Wiefling et al., CC BY 4.0): 33M+ login events,
3.3M+ users. Local development uses a reproducible ~300K-row user-level subsample — see
[`data/DATA.md`](data/DATA.md) for exact methodology and caveats.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Running the API

```bash
# 1. Postgres (local dev; formalized into docker-compose.yml in Phase 5)
docker run -d --name anomalock-postgres \
  -e POSTGRES_USER=anomalock -e POSTGRES_PASSWORD=anomalock_dev -e POSTGRES_DB=anomalock \
  -p 5434:5432 postgres:16-alpine
cp .env.example .env   # DATABASE_URL points at localhost:5434 by default

# 2. Train the artifact the API serves (Isolation Forest fit on the full feature set)
python -m anomalock.models.train_serving_model

# 3. Run the API (creates tables on startup)
python -m uvicorn api.app.main:app --reload

# 4. Simulate live traffic by replaying historical events through /score
python -m api.replay --limit 500
```

`POST /score` accepts a login event (user/timestamp/IP/geo/device/success) and returns a 0-100 risk score
(percentile rank vs. training history), a risk level, `step_up_required`, and human-readable `flagged_reasons`
(e.g. `impossible_travel`, `new_device_new_network`) — see [`api/app/schemas.py`](api/app/schemas.py). Features
are computed causally from that user's (and source IP's) prior events already stored in Postgres, using the
exact same definitions as [`src/anomalock/features/build_features.py`](src/anomalock/features/build_features.py)
so there's no train/serve skew — see [`api/app/scoring.py`](api/app/scoring.py) for the online version.

## Running the dashboard

```bash
cd dashboard
npm install
cp .env.example .env   # VITE_API_URL points at localhost:8000 by default
npm run dev
```

Open the printed localhost URL. The left panel fires scenario logins (each sends a quiet baseline "seed"
event first, so the model has personal history to compare the real attempt against — see
[`dashboard/src/lib/scenarios.ts`](dashboard/src/lib/scenarios.ts)); the right panel is a live feed of every
scored login, pushed over Socket.IO from [`api/app/socket.py`](api/app/socket.py) the moment `/score` runs —
including events from `python -m api.replay`, so replaying historical data animates the dashboard live.

## Roadmap

1. **Data** — acquire/subsample RBA dataset, EDA ✅
2. **Feature engineering & modeling** — baseline rules, Isolation Forest, Random Forest, comparison report ✅
3. **API** — FastAPI scoring endpoint + replay tool ✅
4. **Dashboard** — React + Socket.IO live risk feed with mock step-up-auth flow ✅
5. **Deployment & writeup** — Docker Compose, Fly.io, final README
