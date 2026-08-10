# Data

## Source

[RBA Dataset](https://zenodo.org/record/6782156) — "Login Data Set for Risk-Based Authentication" (Wiefling et
al.), CC BY 4.0. Real-world data: 33M+ login attempts from 3.3M+ users of a large-scale SSO service in Norway,
collected Feb 2020 – Feb 2021.

- `rba-dataset.zip` (1.1GB, MD5 `cc1b1078b3929650e6c08678caffcc57`) → `rba-dataset.csv` (~9GB, not committed —
  see `.gitignore`). Re-download with:

  ```bash
  curl -L -o data/raw/rba-dataset.zip "https://zenodo.org/records/6782156/files/rba-dataset.zip?download=1"
  unzip data/raw/rba-dataset.zip -d data/raw/
  ```

## Two attack-related columns — not interchangeable

- `Is Attack IP`: a noisy IP-reputation heuristic. True for **~8.4%** of rows in our sample. Useful as an input
  feature, but far too common and false-positive-prone to treat as ground truth.
- `Is Account Takeover`: the dataset authors' confirmed-attack label. True for only **141 of 300,003** rows in
  our sample (**~0.05%**) — extremely sparse. This is the label used for supervised evaluation in Phase 2.

## Subsample

`data/processed/rba_sample.parquet` — 300,003 rows / 74,353 users, produced by
[`src/anomalock/ingest/subsample.py`](../src/anomalock/ingest/subsample.py):

```bash
python -m src.anomalock.ingest.subsample --target-rows 300000
```

Sampling is **user-level, not row-level**: every user with a confirmed `Is Account Takeover` event is kept in
full, plus a random selection of additional whole users (seeded, reproducible) until the row budget is hit.
Sampling whole users (rather than random individual rows) matters because per-user behavioral features (login
velocity, time-of-day deviation, device/IP/ASN novelty) require a user's complete login history — a row-level
random sample would silently create gaps in that history and corrupt those features.

### Resume-accuracy note

The subsample is real-world data, not synthetic — but it is a stratified subsample skewed toward users with
more history and toward the ~74K/3.3M users selected, so absolute rates (e.g. attack prevalence) in the
subsample should not be quoted as the full dataset's population statistics. Describe it as "a stratified
subsample of the RBA dataset" rather than "the RBA dataset" when precision matters.

See [`notebooks/01_eda.ipynb`](../notebooks/01_eda.ipynb) for full exploratory analysis.

## External reference data

`data/external/cities15000.txt` — [GeoNames](https://www.geonames.org/) cities with population ≥ 15,000
(~25K rows, CC BY 4.0), committed as-is (8.4MB) since it's small and static. Used by
[`src/anomalock/features/geo.py`](../src/anomalock/features/geo.py) to resolve the dataset's City/Country
strings to lat/lon for the login-velocity feature, since the RBA dataset itself has no coordinates. City-name
matching hits for ~34% of rows in the subsample; the rest fall back to a population-weighted country centroid
(computed from this same file) — coarse, but sufficient to catch cross-country "impossible travel," which is
the feature's actual purpose.
