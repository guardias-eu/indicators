"""Prepare data files required by the GUARDIAS indicators dashboard.

Downloads the two source files and writes them to ``data/``:

* ``data/lme_polygons.geojson``      — LME boundaries (from lme_eu.gpkg)
* ``data/emerging_species_lme_combinations.csv`` — species × LME lookup table

Run from the repository root::

    pip install geopandas
    python scripts/prepare_data.py
"""

import os
import tempfile
import urllib.request
from pathlib import Path

import geopandas as gpd

# ---------------------------------------------------------------------------
# Source URLs
# ---------------------------------------------------------------------------
LME_GPKG_URL = (
    "https://github.com/guardias-eu/build-eu-cube/raw/refs/heads/main"
    "/data/output/lme_eu.gpkg"
)
SPECIES_CSV_URL = (
    "https://raw.githubusercontent.com/guardias-eu/emtrends/main"
    "/data/output/emerging_species_lme_combinations.csv"
)

# ---------------------------------------------------------------------------
# Output paths (relative to repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
LME_GEOJSON_OUT = DATA_DIR / "lme_polygons.geojson"
SPECIES_CSV_OUT = DATA_DIR / "emerging_species_lme_combinations.csv"

# Geometry simplification tolerance in degrees (keeps file size manageable
# while preserving recognisable LME shapes).
SIMPLIFY_TOLERANCE = 0.1


def download(url: str, dest: Path) -> None:
    """Download *url* to *dest*, printing progress."""
    print(f"Downloading {dest.name} …")
    urllib.request.urlretrieve(url, dest)
    print(f"  → saved {dest} ({dest.stat().st_size / 1024:.1f} KB)")


def build_lme_geojson(gpkg_path: Path, out_path: Path) -> None:
    """Convert the source GeoPackage to a simplified GeoJSON.

    Keeps only the ``lme_id`` (= ``objectid``) and ``lme_name`` properties.
    """
    print("Converting GPKG → GeoJSON …")
    gdf = gpd.read_file(gpkg_path)

    gdf_out = gdf[["objectid", "lme_name", "geometry"]].copy()
    gdf_out["lme_id"] = gdf_out["objectid"].astype(int)
    gdf_out = gdf_out[["lme_id", "lme_name", "geometry"]]
    gdf_out["geometry"] = gdf_out["geometry"].simplify(
        tolerance=SIMPLIFY_TOLERANCE, preserve_topology=True
    )

    gdf_out.to_file(out_path, driver="GeoJSON")
    print(f"  → saved {out_path} ({out_path.stat().st_size / 1024:.1f} KB)")
    print(f"  → {len(gdf_out)} LME features:")
    for _, row in gdf_out.iterrows():
        print(f"       lme_id={row['lme_id']:>2}  {row['lme_name']}")


def main() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp_dir:
        # --- LME boundaries ------------------------------------------------
        tmp_gpkg = Path(tmp_dir) / "lme_eu.gpkg"
        download(LME_GPKG_URL, tmp_gpkg)
        build_lme_geojson(tmp_gpkg, LME_GEOJSON_OUT)

    # --- Species × LME combinations ------------------------------------
    download(SPECIES_CSV_URL, SPECIES_CSV_OUT)

    print("\nDone — data files are ready.")


if __name__ == "__main__":
    main()
