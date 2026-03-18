# GUARDIAS Indicators Dashboard

Interactive Quarto dashboard for exploring emergence indicator plots for marine
species across Large Marine Ecosystem (LME) regions.

## Features

- **Species autocomplete** — type any species name; suggestions appear as you type
- **Interactive Leaflet map** — LME regions containing the selected species are
  highlighted; grey regions hold no data for that species
- **Hover tooltips** — show the first 5 species present in each LME (with total count)
- **Click-to-view plots** — clicking a highlighted region opens a popup with the
  pre-generated indicator PNG for that species × LME combination

## Data sources

| File | Source | Update frequency |
|------|--------|------------------|
| `data/lme_polygons.geojson` | Derived from [`lme_eu.gpkg`](https://github.com/guardias-eu/build-eu-cube/blob/main/data/output/lme_eu.gpkg) (guardias-eu/build-eu-cube), simplified at 0.1° tolerance | Manual (via `scripts/prepare_data.py`) |
| `data/species_lme_combinations.csv` | [`species_lme_combinations.csv`](https://github.com/guardias-eu/emtrends/blob/main/data/output/species_lme_combinations.csv) (guardias-eu/emtrends) | Weekly (via GitHub Actions) |
| `data/indicators_plots_png/` | PNG files from [`indicators_plots_png/`](https://github.com/guardias-eu/emtrends/tree/main/data/output/indicators_plots/indicators_plots_png) (guardias-eu/emtrends) | Weekly (via GitHub Actions) |

### Automated data updates

The indicator PNG files and `species_lme_combinations.csv` are automatically updated weekly via a GitHub Actions workflow (`.github/workflows/update-data.yml`). The workflow runs every Monday at 00:00 UTC and can also be triggered manually via workflow dispatch.

To manually trigger an update:
1. Go to the [Actions tab](../../actions/workflows/update-data.yml)
2. Click "Run workflow"
3. Select the branch and click "Run workflow"

### Re-generating the data files

To refresh `data/` from the latest upstream sources, run:

```bash
# For LME polygons (requires geopandas)
pip install geopandas
python scripts/prepare_data.py

# For PNG files and species CSV (automated weekly via GitHub Actions)
pip install requests
python scripts/download_emtrends_data.py
```

Note: The PNG files and species CSV are automatically updated weekly by GitHub Actions, so manual updates are typically not necessary.

## Running the dashboard locally

Install [Quarto](https://quarto.org/docs/get-started/), then:

```bash
quarto preview
```

Quarto opens the dashboard in your browser (usually <http://localhost:4848>).
The page live-reloads on every save.

## Building the static site

```bash
quarto render
```

The rendered site is written to `docs/` and can be served by any static host
(e.g. GitHub Pages).

## Funding
This package is being developed in the framework of the GuardIAS prject. GuardIAS receives funding from the European Union’s Horizon Europe Research and Innovation Programme (ID No 101181413).
