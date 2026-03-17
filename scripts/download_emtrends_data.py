"""Download data files from the guardias-eu/emtrends repository.

Downloads:
* PNG files from indicators_plots_png/ directory
* species_lme_combinations.csv file

These files are updated weekly in the emtrends repository and need to be
synced to this repository for local access.

Run from the repository root::

    pip install requests
    python scripts/download_emtrends_data.py
"""

import csv
import os
import sys
import time
from pathlib import Path
from urllib.request import urlopen, urlretrieve
from urllib.error import HTTPError

# ---------------------------------------------------------------------------
# Source URLs
# ---------------------------------------------------------------------------
EMTRENDS_BASE_URL = "https://raw.githubusercontent.com/guardias-eu/emtrends/main"
SPECIES_CSV_URL = f"{EMTRENDS_BASE_URL}/data/output/species_lme_combinations.csv"
PLOTS_BASE_URL = f"{EMTRENDS_BASE_URL}/data/output/indicators_plots/indicators_plots_png"

# ---------------------------------------------------------------------------
# Output paths (relative to repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
PLOTS_DIR = DATA_DIR / "indicators_plots_png"
SPECIES_CSV_OUT = DATA_DIR / "species_lme_combinations.csv"

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def download_file(url: str, dest: Path, silent: bool = False) -> bool:
    """Download *url* to *dest*.
    
    Returns True if successful, False otherwise.
    """
    try:
        if not silent:
            print(f"Downloading {dest.name} ...")
        urlretrieve(url, dest)
        if not silent:
            print(f"  → saved {dest} ({dest.stat().st_size / 1024:.1f} KB)")
        return True
    except HTTPError as e:
        if not silent:
            print(f"  → Failed to download {url}: {e}", file=sys.stderr)
        return False


def build_png_filename(lme_name: str, species_key: str) -> str:
    """Build the PNG filename from LME name and species key."""
    return f"lme_{lme_name}_species_{species_key}.png"


def download_png_files() -> None:
    """Download all PNG files based on species_lme_combinations.csv."""
    print("\n=== Downloading PNG files ===")
    
    # Create the plots directory if it doesn't exist
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Read the species-LME combinations
    with open(SPECIES_CSV_OUT, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    
    print(f"Found {len(rows)} species-LME combinations")
    
    # Track download statistics
    downloaded = 0
    skipped = 0
    failed = 0
    
    # Download each PNG file
    for i, row in enumerate(rows, 1):
        species_key = row['species_key']
        lme_name = row['lme_name']
        
        filename = build_png_filename(lme_name, species_key)
        dest_path = PLOTS_DIR / filename
        
        # Build the URL - encode spaces and special characters in the filename
        from urllib.parse import quote
        url = f"{PLOTS_BASE_URL}/{quote(filename)}"
        
        # Skip if file already exists (to save bandwidth)
        # Note: We could add a force flag or check file timestamps for updates
        if dest_path.exists():
            skipped += 1
            if i % 10 == 0 or i == len(rows):
                print(f"Progress: {i}/{len(rows)} (downloaded: {downloaded}, skipped: {skipped}, failed: {failed})")
            continue
        
        # Download the file
        success = download_file(url, dest_path, silent=True)
        
        if success:
            downloaded += 1
        else:
            failed += 1
        
        # Print progress every 10 files or at the end
        if i % 10 == 0 or i == len(rows):
            print(f"Progress: {i}/{len(rows)} (downloaded: {downloaded}, skipped: {skipped}, failed: {failed})")
        
        # Small delay to avoid rate limiting
        if i % 50 == 0:
            time.sleep(1)
    
    print(f"\nPNG download complete:")
    print(f"  Downloaded: {downloaded} files")
    print(f"  Skipped (already exist): {skipped} files")
    print(f"  Failed: {failed} files")
    
    if failed > 0:
        print(f"\nWarning: {failed} files failed to download. They may not exist in the source repository.")


def download_species_csv() -> None:
    """Download the species_lme_combinations.csv file."""
    print("\n=== Downloading species_lme_combinations.csv ===")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    download_file(SPECIES_CSV_URL, SPECIES_CSV_OUT)


def main() -> None:
    """Main entry point."""
    print("Starting data download from guardias-eu/emtrends repository\n")
    print(f"Target directory: {DATA_DIR}")
    
    # First, download the CSV file (we need this to know which PNGs to download)
    download_species_csv()
    
    # Then download all PNG files
    download_png_files()
    
    print("\n✓ Data download complete!")


if __name__ == "__main__":
    main()
