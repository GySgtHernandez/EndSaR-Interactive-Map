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

### Quarterly data and how CEPI releases are handled

CEPI posts one file per school year and replaces it as the year fills in: a **Q1** file (Jan/Feb), then a **Q2** file that also contains Q1 (May/June), then the **final** file with Q1-Q4 and School Year Totals (Aug/Sept).

- Each school year has exactly one current file in `data/sources.json`. A later release for the same school year **replaces** the earlier one (the old entry stays, marked `superseded`, with the date and the file that replaced it). A file for a school year not seen before is **added**.
- If CEPI still lists an older release, it is ignored. A file whose school year or release cannot be read from its name is flagged in the pull request for a person to check, and is not added.
- The map's **Reporting Period** menu shows CEPI's own numbers for each period: `site/data/map-data.json` (School Year Totals) and `map-data-q1.json` ... `map-data-q4.json`. Nothing is added up across quarters; student counts overlap between quarters.
- A school year that only has mid-year data appears under Q1-Q4 as "(prov.)", never under School Year Totals, and the map shows a "New data" banner.
- 2017-2018 has no quarterly sheets, so the quarter views start at 2018-2019.

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
- `site/data/entity-locations.json` - marker locations for entities with no district boundary: charter academies (circles), ISD programs (squares) and state districts (diamonds). Built from `data/entity-locations.csv`.
- `data/entity-locations.csv` - edit in Excel to move or add a marker; `entity_type` (PSA, ISD or State District) sets its shape. Sources: NCES EDGE 2024-25 district office geocodes, or the centre of the host district/ISD (CEPI EEM) when no address exists.
- `data/sources.json` - approved CEPI source files. `importedOn` records when each file was added; the newest one sets the map's "Updated" date.
- `site/data/app-info.json` - dates in the App Data panel (Last Updated, Last Refreshed, Last Import). Written by `scripts/write_app_info.py`; the publish step stamps Last Refreshed with the time of the latest weekly CEPI check.
- `data/district-roster.csv` - district, ISD, region roster used for projections.
- `data/entity-types.csv` - LEA, PSA, ISD or State for each district code (from CEPI's Educational Entity Master). Used for the entity counts on the map; a new code missing from this file is listed in the weekly pull request.
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
