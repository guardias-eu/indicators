"""Download data files from the guardias-eu/emtrends repository.

Downloads:
* ZIP files containing ggplot2 objects from indicators_plots/ directory
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
RDS_DIR = DATA_DIR / "indicators_plots_rds"
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


def build_zip_filename(lme_name: str) -> str:
    """Build the ZIP filename from LME name."""
    # ZIP files are named like: lme_Baltic Sea_indicators_plots.zip
    return f"lme_{lme_name}_indicators_plots.zip"


def build_rds_filename(lme_name: str, species_key: str) -> str:
    """Build the RDS filename from LME name and species key."""
    return f"lme_{lme_name}_species_{species_key}.rds"


def download_and_extract_rds_files() -> None:
    """Download ZIP files and extract RDS files for all species-LME combinations.
    
    ZIP files are organized by LME in the emtrends repository.
    Each ZIP contains multiple .rds files (one per species in that LME).
    """
    print("\n=== Downloading and extracting RDS files ===")
    
    # Clean the RDS directory to ensure we get fresh files
    if RDS_DIR.exists():
        print(f"Cleaning existing RDS directory: {RDS_DIR}")
        shutil.rmtree(RDS_DIR)
    
    # Create directories
    RDS_DIR.mkdir(parents=True, exist_ok=True)
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
    
    # Track statistics
    downloaded_zips = 0
    failed_zips = 0
    extracted_rds = 0
    
    # Download and extract each LME's ZIP file
    for i, (lme_name, species_keys) in enumerate(lme_species.items(), 1):
        zip_filename = build_zip_filename(lme_name)
        zip_path = TEMP_DIR / zip_filename
        
        # Build the URL - encode spaces and special characters
        from urllib.parse import quote
        url = f"{PLOTS_BASE_URL}/{quote(zip_filename)}"
        
        print(f"\n[{i}/{len(lme_species)}] Processing {lme_name} ({len(species_keys)} species)")
        
        # Download the ZIP file
        if not download_file(url, zip_path, silent=False):
            print(f"  ⚠ Failed to download ZIP for {lme_name}")
            failed_zips += 1
            continue
        
        downloaded_zips += 1
        
        # Extract RDS files from the ZIP
        try:
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                # List all files in the ZIP
                zip_contents = zip_ref.namelist()
                rds_files = [f for f in zip_contents if f.endswith('.rds')]
                
                print(f"  → Found {len(rds_files)} RDS files in ZIP")
                
                # Extract each RDS file
                for rds_file in rds_files:
                    # Extract to RDS directory
                    zip_ref.extract(rds_file, TEMP_DIR)
                    
                    # Move to final location (ZIP might have subdirectories)
                    source = TEMP_DIR / rds_file
                    dest = RDS_DIR / os.path.basename(rds_file)
                    
                    if source.exists():
                        shutil.move(str(source), str(dest))
                        extracted_rds += 1
                
        except zipfile.BadZipFile as e:
            print(f"  ⚠ Bad ZIP file for {lme_name}: {e}", file=sys.stderr)
            failed_zips += 1
        except Exception as e:
            print(f"  ⚠ Error extracting ZIP for {lme_name}: {e}", file=sys.stderr)
            failed_zips += 1
        
        # Clean up the ZIP file
        if zip_path.exists():
            zip_path.unlink()
    
    # Clean up temp directory
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    
    print(f"\n=== Download and extraction complete ===")
    print(f"  Downloaded ZIPs: {downloaded_zips}")
    print(f"  Failed ZIPs: {failed_zips}")
    print(f"  Extracted RDS files: {extracted_rds}")
    
    if failed_zips > 0:
        print(f"\n⚠ Warning: {failed_zips} ZIP files failed to download/extract.")
        print(f"  They may not exist in the source repository.")


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
    
    # Then download and extract RDS files from ZIP archives
    download_and_extract_rds_files()
    
    print("\n✓ Data download complete!")


if __name__ == "__main__":
    main()
