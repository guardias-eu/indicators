# GUARDIAS Indicators Dashboard

Interactive Quarto dashboard for exploring emergence indicator plots for marine
species across Large Marine Ecosystem (LME) regions.

## Features

- **Species autocomplete** — type any species name; suggestions appear as you type
- **Interactive Leaflet map** — LME regions containing the selected species are
  highlighted; grey regions hold no data for that species
- **Hover tooltips** — show the first 5 species present in each LME (with total count)
- **Click-to-view plots** — clicking a highlighted region opens a popup with an
  interactive Plotly chart for that species × LME combination
- **Interactive plots** — zoom, pan, hover for exact values, and download plots as PNG

## Data sources

| File | Source | Update frequency |
|------|--------|------------------|
| `data/lme_polygons.geojson` | Derived from [`lme_eu.gpkg`](https://github.com/guardias-eu/build-eu-cube/blob/main/data/output/lme_eu.gpkg) (guardias-eu/build-eu-cube), simplified at 0.1° tolerance | Manual (via `scripts/prepare_data.py`) |
| `data/species_lme_combinations.csv` | [`species_lme_combinations.csv`](https://github.com/guardias-eu/emtrends/blob/main/data/output/species_lme_combinations.csv) (guardias-eu/emtrends) | Weekly (via GitHub Actions) |
| `data/indicators_plots_rds/` | RDS files extracted from ZIP archives in [`indicators_plots/`](https://github.com/guardias-eu/emtrends/tree/main/data/output/indicators_plots) (guardias-eu/emtrends) | Weekly (via GitHub Actions) |
| `data/indicators_plots_json/` | Plotly JSON files converted from ggplot2 objects in RDS files | Weekly (via GitHub Actions) |

### Data flow

The indicator plots follow this processing pipeline:

1. **Source**: ggplot2 objects stored in ZIP archives in the [emtrends repository](https://github.com/guardias-eu/emtrends/tree/main/data/output/indicators_plots)
2. **Download**: Python script downloads ZIP files and extracts `.rds` files
3. **Convert**: R script reads `.rds` files, converts ggplot2 to Plotly, and exports as JSON
4. **Display**: Observable JavaScript loads JSON and renders interactive charts

### Automated data updates

The indicator plot files and `species_lme_combinations.csv` are automatically updated weekly via a GitHub Actions workflow (`.github/workflows/update-data.yml`). The workflow runs every Wednesday at 00:00 UTC and can also be triggered manually via workflow dispatch.

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

# For indicator plots and species CSV (automated weekly via GitHub Actions)
# Step 1: Download ZIP files and extract RDS files
pip install requests
python scripts/download_emtrends_data.py

# Step 2: Convert ggplot2 objects to Plotly JSON (requires R)
# Install R packages first:
#   install.packages(c('ggplot2', 'plotly', 'jsonlite'))
Rscript scripts/convert_plots_to_plotly.R
```

Note: The indicator plots and species CSV are automatically updated weekly by GitHub Actions, so manual updates are typically not necessary.

## Dependencies

### Python
- Python 3.11+
- `requests` (for downloading data)
- `geopandas` (only for regenerating LME polygons)

### R
- R 4.0+
- `ggplot2` (for reading ggplot objects)
- `plotly` (for converting to interactive plots)
- `jsonlite` (for JSON export)

### Quarto
- [Quarto](https://quarto.org/docs/get-started/) for rendering the dashboard

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
This package is being developed in the framework of the GuardIAS project. GuardIAS receives funding from the European Union's Horizon Europe Research and Innovation Programme (ID No 101181413).
