# EndSaR Interactive Map

Interactive Michigan seclusion and restraint data map, published free with GitHub Pages:

<https://gysgthernandez.github.io/EndSaR-Interactive-Map/>

The map runs entirely in the visitor's browser (no server), so GitHub Pages hosts it fully interactive.

## Everyday use

| I want to... | Do this |
|---|---|
| Look at the map on my computer | Double-click `Preview-Map.cmd`. Close the black window to stop. |
| Check for new CEPI data now | On GitHub: **Actions** tab > **Check for CEPI data updates** > **Run workflow**. Or double-click `Update-Map-Data.cmd` on your computer (needs Python). |
| Publish new data | Open the pull request the update creates, read the summary table, then click **Merge**. The site updates in a few minutes. |

### How new data reaches the site

1. Every Monday morning GitHub checks the official MI School Data catalog for CEPI-60 seclusion and restraint files.
2. If a new full-year file is listed, it downloads every approved file, rebuilds the map data and runs the accuracy checks.
3. It opens a **pull request** with a plain summary (statewide totals for every year). Nothing on the public site changes yet.
4. When you merge the pull request, the site republishes automatically.

Mid-year (quarterly) files are recorded for review but are never published as full-year data.

Note: GitHub pauses scheduled jobs in repositories with no activity for 60 days. If the Monday check ever stops, open the Actions tab and re-enable it, or use **Run workflow**.

## One-time GitHub settings

1. **Settings > Pages > Build and deployment > Source:** choose **GitHub Actions**.
2. **Settings > Actions > General > Workflow permissions:** choose **Read and write permissions** and tick **Allow GitHub Actions to create and approve pull requests**.

## Accuracy checks

Every rebuild must pass before anything is proposed:

- the data covers at least eight sorted school years and every map view has data;
- totals and every area's numbers are compared with the last approved version (`tests/baseline-summary.json`), and any difference is listed in `reports/validation-report.json`;
- unit tests confirm the compact data file shows exactly the same numbers as the full build.

The 2025-2026 update (November 2026) was checked against the September 2026 Netlify build: all 20,538 area-year records matched exactly.

## Important files

- `site/` - the public website (map page, boundaries, data).
- `site/data/map-data.json` - all map numbers in a compact format (about 5 MB; the page expands it on load).
- `site/data/entity-locations.json` - dot locations for charter academies, ISD programs and state districts, which have no district boundary. Built from `data/entity-locations.csv`.
- `data/entity-locations.csv` - edit in Excel to move or add a dot. Sources: NCES EDGE 2024-25 district office geocodes, or the centre of the host district/ISD (CEPI EEM) when no address exists.
- `data/sources.json` - approved CEPI source files.
- `data/district-roster.csv` - district, ISD, region roster used for projections.
- `scripts/run_pipeline.py` - the full rebuild (download > combine > approximate suppressed values > build map data > validate).
- `tests/` - accuracy tests and the approved baseline.

### Boundary corrections

`site/district-boundaries-optimized.js` contains three district code corrections (marked `idCorrection` inside the file):

- Linden Community Schools: the source boundary file uses code 21690; CEPI uses 25250.
- Highland Park City Schools area (82070) shows Highland Park Public School Academy System (82749).
- Muskegon Heights School District area (61020) shows Muskegon Heights Public School Academy System (61905).

## Rebuild by hand (advanced)

```powershell
python -m pip install -r requirements.txt
python scripts/run_pipeline.py                         # strict: must match the approved baseline
python scripts/run_pipeline.py --discover --allow-change  # look for new CEPI files and accept changes for review
```
