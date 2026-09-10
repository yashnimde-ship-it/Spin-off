# Bootstrap

How to get this repository running from a clean clone.

The trained models and processed data are **not in git** — they are binary
artifacts excluded by `.gitignore`. They ship as a separate bundle, described
below. Without them the API starts but every model-backed endpoint returns
`500 model_not_loaded` naming the file it wanted.

## Requirements

- **Python 3.11** (the project is developed and tested on 3.11)
- **pip** (or `uv`, if you prefer — see below)
- **Tesseract OCR 5.x** — *only* needed if you re-run the MSMP OCR recovery
  step. The five OCR-recovered months are already baked into
  `msmp_mn_monthly_wide.parquet` in the artifact bundle, so a normal setup
  does not need Tesseract. If you do want it:
  Windows installer puts it at `%LOCALAPPDATA%\Programs\Tesseract-OCR`;
  `src/data/preprocess/ocr_msmp_scanned.py` addresses the binary directly
  rather than relying on `PATH`.

## 1. Install dependencies

```bash
python -m venv .venv
.venv\Scripts\activate            # Windows
# source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

With `uv` instead:

```bash
uv venv
uv pip install -r requirements.txt
```

Prophet compiles a Stan model on first import, so the initial install is slow.

## 2. Get the artifact bundle

Download `moil_artifacts_bundle.tar.gz` from [SHARE_LINK] and extract at repo
root. This will populate `models/` and `data/processed/`.

```bash
tar -xzf moil_artifacts_bundle.tar.gz
```

It is ~2.5 MB and contains:

| path | what it is |
|---|---|
| `models/prophet_baseline_v1_0_shipped.pkl` | promoted production forecast model |
| `models/shortfall_classifier_v1.pkl` | shortfall risk classifier |
| `models/prospectivity_v6.pkl` | promoted prospectivity model |
| `models/autoencoder_v1.pt` | encoder for the 64 AE feature columns |
| `data/processed/prophet_metrics_baseline_v1_0.json` | shipped backtest metrics |
| `data/processed/prophet_backtest_rows_baseline_v1_0.parquet` | 82 backtest origins |
| `data/processed/msmp_mn_monthly_wide.parquet` | the 123-month production series |
| `data/processed/msmp_mn_monthly_long.parquet` | same series, long format |
| `data/processed/shortfall_features.parquet` | classifier feature table |
| `data/processed/shortfall_labels.parquet` | rolling-origin shortfall labels |
| `data/processed/moil_monthly_series.parquet` | 20 MOIL months, proxy validation only |
| `data/raw/moil/msmp_archive_full.csv` | source-of-truth list of 134 IBM bulletins |
| `data/raw/india/geology/*.geojson` | geological and occurrence-buffer masks |

**Not** in the bundle, because they are large and regenerable:

- the 125 MSMP PDFs (~547 MB) — `python -m src.data.ingest.download_msmp_archive`
  re-downloads them from the URLs in `msmp_archive_full.csv`
- Sentinel-2 rasters and DEM tiles — fetched by the Phase 1/2 ingest scripts
- `data/cache/` — API response caches, regenerated on demand

## 3. Configure the environment

Create `.env` at the repo root:

```
DATABASE_URL=postgresql+psycopg://postgres:PASSWORD@HOST:5432/postgres
```

Only the DB-backed endpoints (`/boreholes`, `/priors`, `/foreign`) and the
rainfall regressor need this. Without it the API still starts, and two tests
skip rather than fail.

## 4. Verify the setup

```bash
./.venv/Scripts/python.exe -m uvicorn src.api.main:app
```

Then hit `/dashboard/summary` — should return `degraded: []`.

An empty `degraded` array means every model and data artifact loaded. If a
name appears in it, that component failed; the startup log names the file.

Startup detail worth knowing: six artifacts load eagerly in about 1.5 seconds,
then a **background thread warms caches** — four forecast horizons (~3 s), the
shortfall SHAP explanation (~3 s), and three heatmap viewports (~20–24 s
each). The API answers requests immediately; the first `/prospectivity/heatmap`
call before warming finishes will take ~38 s rather than ~10 ms.

Interactive API docs: `http://127.0.0.1:8000/docs` — 24 operations.

## 5. Run the tests

```bash
pytest -q
```

Expected: **193 passed, 2 skipped**.

The 2 skips are DB-backed tests that need `DATABASE_URL`; they skip whenever
Supabase is unreachable and are unrelated to the Phase 4 backend.

## Known limitations

See `docs/known_issues.md` for the full list with evidence. The short version:

- three MOIL mines (Gumgaon, Kandri, Beldongri) fall outside the imagery
  footprint and cannot be scored
- forecast CI80 coverage runs 60–71% against a nominal 80%
- the forecast loses to seasonal-naive below a 12-month horizon
- `POST /predict/bbox` returns a non-griddable point set; the map uses
  `/prospectivity/heatmap` instead

## Where to start reading

- `docs/phase_4/api_contracts.md` — the API contract (v1.5), source of truth
  for the frontend
- `docs/phase_4/bucket_1_summary.md` — what is built and what it serves
- `docs/known_issues.md` — every known defect with the evidence that found it
