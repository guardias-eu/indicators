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
RDATA_DIR = DATA_DIR / "indicators_plots_rdata"
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


def download_and_extract_rdata_files() -> None:
    """Download ZIP files and extract RData files for all species-LME combinations.
    
    ZIP files are organized by LME in the emtrends repository and split into chunks.
    Each ZIP contains an .RData file with multiple ggplot2 objects.
    """
    print("\n=== Downloading and extracting RData files ===")
    
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
    
    # Track statistics
    downloaded_zips = 0
    failed_zips = 0
    extracted_rdata = 0
    
    # Download and extract each LME's ZIP files
    for i, (lme_name, species_keys) in enumerate(lme_species.items(), 1):
        print(f"\n[{i}/{len(lme_species)}] Processing {lme_name} ({len(species_keys)} species)")
        
        # Try to download multiple chunks for this LME
        # We don't know how many chunks exist, so try until we get a 404
        chunk = 1
        lme_downloaded = 0
        
        while True:
            zip_filename = build_zip_filename(lme_name, chunk)
            zip_path = TEMP_DIR / zip_filename
            
            # Build the URL - encode spaces and special characters
            from urllib.parse import quote
            url = f"{PLOTS_BASE_URL}/{quote(zip_filename)}"
            
            # Try to download this chunk
            if not download_file(url, zip_path, silent=True):
                # If chunk 1 fails, warn; otherwise we've just run out of chunks
                if chunk == 1:
                    print(f"  ⚠ No ZIP files found for {lme_name}")
                    failed_zips += 1
                break
            
            lme_downloaded += 1
            downloaded_zips += 1
            print(f"  → Downloaded chunk {chunk}")
            
            # Extract RData files from the ZIP
            try:
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    # List all files in the ZIP
                    zip_contents = zip_ref.namelist()
                    rdata_files = [f for f in zip_contents if f.endswith('.RData')]
                    
                    print(f"     Found {len(rdata_files)} RData file(s) in chunk {chunk}")
                    
                    # Extract each RData file
                    for rdata_file in rdata_files:
                        # Extract to TEMP_DIR
                        zip_ref.extract(rdata_file, TEMP_DIR)
                        
                        # Move to final location (ZIP might have subdirectories)
                        source = TEMP_DIR / rdata_file
                        dest = RDATA_DIR / os.path.basename(rdata_file)
                        
                        if source.exists():
                            shutil.move(str(source), str(dest))
                            extracted_rdata += 1
                
            except zipfile.BadZipFile as e:
                print(f"  ⚠ Bad ZIP file for {lme_name} chunk {chunk}: {e}", file=sys.stderr)
                failed_zips += 1
            except Exception as e:
                print(f"  ⚠ Error extracting ZIP for {lme_name} chunk {chunk}: {e}", file=sys.stderr)
                failed_zips += 1
            
            # Clean up the ZIP file
            if zip_path.exists():
                zip_path.unlink()
            
            # Move to next chunk
            chunk += 1
        
        if lme_downloaded > 0:
            print(f"  ✓ Downloaded {lme_downloaded} chunk(s) for {lme_name}")
    
    # Clean up temp directory
    if TEMP_DIR.exists():
        shutil.rmtree(TEMP_DIR)
    
    print(f"\n=== Download and extraction complete ===")
    print(f"  Downloaded ZIPs: {downloaded_zips}")
    print(f"  Failed ZIPs: {failed_zips}")
    print(f"  Extracted RData files: {extracted_rdata}")
    
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
    
    # Then download and extract RData files from ZIP archives
    download_and_extract_rdata_files()
    
    print("\n✓ Data download complete!")


if __name__ == "__main__":
    main()
