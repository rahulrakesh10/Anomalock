# Anomalock

ML-based login risk & anomaly detection system — a lightweight version of the risk-based authentication (RBA)
engines used by Okta, Microsoft Entra, and Auth0. Scores each login attempt on behavioral signals (impossible
travel, brute-force patterns, new-device/off-hours logins) and flags high-risk attempts for step-up
verification instead of either annoying every user or missing slow, low-volume attacks.

## Status

**Phase 1 (data) — in progress.** See [`data/DATA.md`](data/DATA.md) for the dataset writeup and
[`notebooks/01_eda.ipynb`](notebooks/01_eda.ipynb) for exploratory analysis.

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

## Roadmap

1. **Data** — acquire/subsample RBA dataset, EDA
2. **Feature engineering & modeling** — baseline rules, Isolation Forest, Random Forest, comparison report
3. **API** — FastAPI scoring endpoint + replay tool
4. **Dashboard** — React + Socket.IO live risk feed with mock step-up-auth flow
5. **Deployment & writeup** — Docker Compose, Fly.io, final README
