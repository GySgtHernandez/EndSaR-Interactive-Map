# EndSaR Interactive Map

Interactive Michigan seclusion and restraint data map published with GitHub Pages.

## Website

After GitHub Pages is enabled with **GitHub Actions** as its source, the map is published at:

<https://gysgthernandez.github.io/EndSaR-Interactive-Map/>

## Repository structure

- `site/` contains the public website deployed to GitHub Pages.
- `site/map-data.js` is the generated data artifact used by the map.
- `.github/workflows/deploy-pages.yml` deploys the website after changes reach `main`.

The map application and boundary files normally remain unchanged when new CEPI data is added. A validated data build replaces `site/map-data.js`, after which the Pages workflow deploys the update.

## Current update process

The current data artifact was generated from the existing combined and approximated workbook pipeline. Do not substitute a newly published CEPI workbook directly for `map-data.js`; the workbook must first pass through the combination, approximation, geography, and validation steps.
