"""Download data files from the guardias-eu/emtrends repository.

Downloads:
* ZIP files containing ggplot2 objects from indicators_plots/ directory
  (indicator plots, appearing species plots, reappearing species plots)
* species_lme_combinations.csv file

These files are updated weekly in the emtrends repository and need to be
synced to this repository for local access.

The script always re-downloads all files to ensure they are up-to-date,
removing any existing files first.

Run from the repository root::

    pip install requests
    python scripts/download_emtrends_data.py
"""

import csv
import os
import shutil
import sys
import time
import zipfile
from pathlib import Path
from urllib.request import urlopen, urlretrieve
from urllib.error import HTTPError
from urllib.parse import quote

# ---------------------------------------------------------------------------
# Source URLs
# ---------------------------------------------------------------------------
EMTRENDS_BASE_URL = "https://raw.githubusercontent.com/guardias-eu/emtrends/main"
SPECIES_CSV_URL = f"{EMTRENDS_BASE_URL}/data/output/species_lme_combinations.csv"
PLOTS_BASE_URL = f"{EMTRENDS_BASE_URL}/data/output/indicators_plots"

# ---------------------------------------------------------------------------
# Output paths (relative to repo root)
# ---------------------------------------------------------------------------
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR = REPO_ROOT / "data"
RDATA_DIR = DATA_DIR / "indicators_plots_rdata"
APPEARING_RDATA_DIR = DATA_DIR / "appearing_species_rdata"
REAPPEARING_RDATA_DIR = DATA_DIR / "reappearing_species_rdata"
SPECIES_CSV_OUT = DATA_DIR / "species_lme_combinations.csv"
TEMP_DIR = DATA_DIR / "temp_downloads"

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


def build_zip_filename(lme_name: str, chunk: int) -> str:
    """Build the ZIP filename from LME name and chunk number."""
    # ZIP files are named like: indicators_plots_ggplot2_Baltic Sea_chunk_1.zip
    return f"indicators_plots_ggplot2_{lme_name}_chunk_{chunk}.zip"


def build_object_name(lme_name: str, species_key: str) -> str:
    """Build the expected object name from LME name and species key.
    
    Object names in RData files follow the pattern: lme_{lme_name}_species_{species_key}
    """
    return f"lme_{lme_name}_species_{species_key}"


def _extract_zip_to_dir(zip_path: Path, dest_dir: Path) -> int:
    """Extract RData/rds files from a ZIP to dest_dir. Returns count extracted."""
    extracted = 0
    try:
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_contents = zip_ref.namelist()
            rdata_files = [f for f in zip_contents
                           if f.endswith('.RData') or f.endswith('.rds')]
            for rdata_file in rdata_files:
                zip_ref.extract(rdata_file, TEMP_DIR)
                source = TEMP_DIR / rdata_file
                dest = dest_dir / os.path.basename(rdata_file)
                if source.exists():
                    shutil.move(str(source), str(dest))
                    extracted += 1
    except (zipfile.BadZipFile, Exception) as e:
        print(f"  ⚠ Error extracting {zip_path.name}: {e}", file=sys.stderr)
    return extracted


def download_and_extract_rdata_files() -> None:
    """Download ZIP files and extract RData files for all species-LME combinations.

    ZIP files are organized by LME in the emtrends repository and split into chunks.
    Each ZIP contains an .RData file with multiple ggplot2 objects.
    """
    print("\n=== Downloading and extracting indicator RData files ===")

    # Clean the RData directory to ensure we get fresh files
    if RDATA_DIR.exists():
        print(f"Cleaning existing RData directory: {RDATA_DIR}")
        shutil.rmtree(RDATA_DIR)

    # Create directories
    RDATA_DIR.mkdir(parents=True, exist_ok=True)
    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    # Read the species-LME combinations to know which files we need
    with open(SPECIES_CSV_OUT, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    # Group by LME to minimize ZIP downloads
    lme_species = {}
    for row in rows:
        lme_name = row['lme_name']
        species_key = row['species_key']
        if lme_name not in lme_species:
            lme_species[lme_name] = []
        lme_species[lme_name].append(species_key)

    print(f"Found {len(lme_species)} unique LMEs with {len(rows)} total species-LME combinations")

    downloaded_zips = 0
    failed_zips = 0
    extracted_rdata = 0

    for i, (lme_name, species_keys) in enumerate(lme_species.items(), 1):
        print(f"\n[{i}/{len(lme_species)}] Processing {lme_name} ({len(species_keys)} species)")

        chunk = 1
        lme_downloaded = 0

        while True:
            zip_filename = build_zip_filename(lme_name, chunk)
            zip_path = TEMP_DIR / zip_filename
            url = f"{PLOTS_BASE_URL}/{quote(zip_filename)}"

            if not download_file(url, zip_path, silent=True):
                if chunk == 1:
                    print(f"  ⚠ No ZIP files found for {lme_name}")
                    failed_zips += 1
                break

            lme_downloaded += 1
            downloaded_zips += 1
            print(f"  → Downloaded chunk {chunk}")

            n = _extract_zip_to_dir(zip_path, RDATA_DIR)
            extracted_rdata += n
            print(f"     Extracted {n} RData file(s) from chunk {chunk}")

            if zip_path.exists():
                zip_path.unlink()
            chunk += 1

        if lme_downloaded > 0:
            print(f"  ✓ Downloaded {lme_downloaded} chunk(s) for {lme_name}")

    # Clean up temp directory
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)

    print(f"\n=== Indicator download complete ===")
    print(f"  Downloaded ZIPs: {downloaded_zips}")
    print(f"  Failed ZIPs: {failed_zips}")
    print(f"  Extracted RData files: {extracted_rdata}")


def download_and_extract_appearing_reappearing() -> None:
    """Download appearing and reappearing species plot ZIP files per LME."""
    print("\n=== Downloading appearing/reappearing species plots ===")

    # Read LME names from CSV
    with open(SPECIES_CSV_OUT, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        lme_names = sorted({row['lme_name'] for row in reader})

    for dest_dir, prefix, label in [
        (APPEARING_RDATA_DIR, "appearing_species_plots_ggplot2_lme_", "appearing"),
        (REAPPEARING_RDATA_DIR, "reappearing_species_plots_ggplot2_lme_", "reappearing"),
    ]:
        print(f"\n--- {label} species ---")

        if dest_dir.exists():
            shutil.rmtree(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        for lme_name in lme_names:
            zip_filename = f"{prefix}{lme_name}.zip"
            zip_path = TEMP_DIR / zip_filename
            url = f"{PLOTS_BASE_URL}/{quote(zip_filename)}"

            if download_file(url, zip_path, silent=True):
                n = _extract_zip_to_dir(zip_path, dest_dir)
                print(f"  ✓ {lme_name}: extracted {n} file(s)")
                if zip_path.exists():
                    zip_path.unlink()
            else:
                print(f"  ⚠ No {label} species ZIP for {lme_name}")

    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)


def download_species_csv() -> None:
    """Download the species_lme_combinations.csv file."""
    print("\n=== Downloading species_lme_combinations.csv ===")
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    download_file(SPECIES_CSV_URL, SPECIES_CSV_OUT)


def main() -> None:
    """Main entry point."""
    print("Starting data download from guardias-eu/emtrends repository\n")
    print(f"Target directory: {DATA_DIR}")

    # First, download the CSV file (we need this to know which files to download)
    download_species_csv()

    # Then download and extract RData files from ZIP archives
    download_and_extract_rdata_files()

    # Download appearing/reappearing species plot ZIP files
    download_and_extract_appearing_reappearing()

    print("\n✓ Data download complete!")


if __name__ == "__main__":
    main()
