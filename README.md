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

| File | Source |
|------|--------|
| `data/lme_polygons.geojson` | Derived from [`lme_eu.gpkg`](https://github.com/guardias-eu/build-eu-cube/blob/main/data/output/lme_eu.gpkg) (guardias-eu/build-eu-cube), simplified at 0.1° tolerance |
| `data/species_lme_combinations.csv` | [`species_lme_combinations.csv`](https://github.com/guardias-eu/emtrends/blob/main/data/output/species_lme_combinations.csv) (guardias-eu/emtrends) |
| Indicator PNGs | Loaded at runtime from [`indicators_plots_png/`](https://github.com/guardias-eu/emtrends/tree/main/data/output/indicators_plots/indicators_plots_png) (guardias-eu/emtrends) — not stored locally |

### Re-generating the data files

To refresh `data/` from the latest upstream sources, run:

```bash
pip install geopandas
python scripts/prepare_data.py
```

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
