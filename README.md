# EndSaR Interactive Map

Interactive Michigan seclusion and restraint data map published with GitHub Pages.

## Website

After GitHub Pages is enabled with **GitHub Actions** as its source, the map is published at:

<https://gysgthernandez.github.io/EndSaR-Interactive-Map/>

## Repository structure

- `site/` contains the public website deployed to GitHub Pages.
- `site/data/map-data.json` is the generated data artifact loaded by the map.
- `.github/workflows/deploy-pages.yml` deploys the website after changes reach `main`.

The map application and boundary files normally remain unchanged when new CEPI data is added. A validated data build replaces `site/data/map-data.json`, after which the Pages workflow deploys the update.

## Automated data pipeline

The scheduled **Check for CEPI data updates** workflow runs every Monday and can also be started manually. It:

1. Reads the official MI School Data catalog.
2. Downloads every approved CEPI-60 source listed in `data/sources.json`.
3. Records source URLs, sizes, and SHA-256 hashes.
4. Normalizes district and ISD worksheets.
5. Reconciles suppressed district values against ISD totals.
6. Joins district, ISD, region, and county geography.
7. Generates the versionable `site/data/map-data.json` artifact.
8. Validates the output against the approved regression baseline.
9. Opens a review pull request when sources or generated data change.

The live site is not changed until that pull request is reviewed and merged. Newly discovered quarterly files are recorded for review but are not silently published as full-year data.

## Run locally

```powershell
python -m pip install -r requirements.txt
python scripts/run_pipeline.py
```

To check the official catalog for new source candidates:

```powershell
python scripts/run_pipeline.py --discover --allow-change
```

The strict default command must reproduce `tests/baseline-summary.json`. Use `--allow-change` only when intentionally reviewing a new or revised CEPI release.

## Important files

- `data/sources.json`: approved sources and publication-period policy.
- `data/district-roster.csv`: versioned district, ISD-region, and entity roster used by the projection build.
- `reports/source-report.json`: downloaded source hashes and new candidates.
- `reports/validation-report.json`: regression result and differences.
- `tests/baseline-summary.json`: last approved semantic baseline.
- `scripts/run_pipeline.py`: end-to-end pipeline entry point.
