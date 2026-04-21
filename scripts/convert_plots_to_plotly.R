#!/usr/bin/env Rscript

#' Convert ggplot2 objects to Plotly JSON files
#'
#' This script reads .rds files containing ggplot2 objects,
#' converts them to interactive Plotly objects, and exports
#' them as JSON files that can be loaded by JavaScript.
#'
#' Required packages: ggplot2, plotly, jsonlite
#'
#' Run from repository root:
#'   Rscript scripts/convert_plots_to_plotly.R

suppressPackageStartupMessages({
  library(ggplot2)
  library(plotly)
  library(jsonlite)
})

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Determine the repository root (parent of scripts/)
script_path <- commandArgs(trailingOnly = FALSE)
script_dir <- dirname(sub("--file=", "", script_path[grep("--file=", script_path)]))
if (length(script_dir) == 0) {
  # Fallback if running interactively
  script_dir <- "scripts"
}
repo_root <- normalizePath(file.path(script_dir, ".."))

# Directory paths
rds_dir <- file.path(repo_root, "data", "indicators_plots_rds")
json_dir <- file.path(repo_root, "data", "indicators_plots_json")

cat("Repository root:", repo_root, "\n")
cat("RDS directory:", rds_dir, "\n")
cat("JSON directory:", json_dir, "\n\n")

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

#' Convert a ggplot2 object to Plotly JSON
#'
#' @param ggplot_obj A ggplot2 object
#' @param output_file Path where JSON should be saved
#' @return TRUE if successful, FALSE otherwise
convert_ggplot_to_plotly_json <- function(ggplot_obj, output_file) {
  tryCatch({
    # Convert ggplot to plotly
    plotly_obj <- ggplotly(ggplot_obj, tooltip = "all")
    
    # Configure plotly layout for better popup display
    plotly_obj <- plotly_obj %>%
      layout(
        autosize = TRUE,
        margin = list(l = 50, r = 50, t = 50, b = 50),
        hovermode = "closest"
      )
    
    # Convert to JSON
    plotly_json <- plotly_obj %>%
      plotly_json(pretty = FALSE)
    
    # Write to file
    writeLines(plotly_json, output_file)
    
    return(TRUE)
  }, error = function(e) {
    warning("Failed to convert plot: ", conditionMessage(e))
    return(FALSE)
  })
}

# ---------------------------------------------------------------------------
# Main conversion process
# ---------------------------------------------------------------------------

cat("=== Converting ggplot2 objects to Plotly JSON ===\n\n")

# Check if RDS directory exists
if (!dir.exists(rds_dir)) {
  stop("RDS directory not found: ", rds_dir, "\n",
       "Please run download_emtrends_data.py first to download the RDS files.")
}

# Create JSON output directory
if (dir.exists(json_dir)) {
  cat("Cleaning existing JSON directory:", json_dir, "\n")
  unlink(json_dir, recursive = TRUE)
}
dir.create(json_dir, recursive = TRUE, showWarnings = FALSE)

# Get all RDS files
rds_files <- list.files(rds_dir, pattern = "\\.rds$", full.names = TRUE)

if (length(rds_files) == 0) {
  stop("No RDS files found in: ", rds_dir, "\n",
       "Please run download_emtrends_data.py first to download the RDS files.")
}

cat("Found", length(rds_files), "RDS files to convert\n\n")

# Track conversion statistics
converted <- 0
failed <- 0
start_time <- Sys.time()

# Convert each RDS file
for (i in seq_along(rds_files)) {
  rds_file <- rds_files[i]
  rds_basename <- basename(rds_file)
  
  # Build output filename (replace .rds with .json)
  json_basename <- sub("\\.rds$", ".json", rds_basename)
  json_file <- file.path(json_dir, json_basename)
  
  # Progress update every 10 files or at start/end
  if (i %% 10 == 1 || i == length(rds_files)) {
    cat(sprintf("[%d/%d] Converting %s\n", i, length(rds_files), rds_basename))
  }
  
  # Read the ggplot object
  tryCatch({
    ggplot_obj <- readRDS(rds_file)
    
    # Verify it's a ggplot object
    if (!inherits(ggplot_obj, "gg") && !inherits(ggplot_obj, "ggplot")) {
      warning("File does not contain a ggplot object: ", rds_basename)
      failed <- failed + 1
      next
    }
    
    # Convert to Plotly JSON
    if (convert_ggplot_to_plotly_json(ggplot_obj, json_file)) {
      converted <- converted + 1
    } else {
      failed <- failed + 1
    }
    
  }, error = function(e) {
    warning("Failed to read RDS file ", rds_basename, ": ", conditionMessage(e))
    failed <- failed + 1
  })
  
  # Progress report every 50 files
  if (i %% 50 == 0) {
    elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
    rate <- i / elapsed
    remaining <- (length(rds_files) - i) / rate
    cat(sprintf("  Progress: %d/%d (converted: %d, failed: %d, ~%.0fs remaining)\n",
                i, length(rds_files), converted, failed, remaining))
  }
}

# Final statistics
end_time <- Sys.time()
elapsed <- as.numeric(difftime(end_time, start_time, units = "secs"))

cat("\n=== Conversion complete ===\n")
cat(sprintf("  Converted: %d files\n", converted))
cat(sprintf("  Failed: %d files\n", failed))
cat(sprintf("  Time elapsed: %.1f seconds\n", elapsed))
cat(sprintf("  Average rate: %.1f files/second\n", length(rds_files) / elapsed))

if (failed > 0) {
  cat("\n⚠ Warning:", failed, "files failed to convert.\n")
  cat("  Check warnings above for details.\n")
}

cat("\n✓ Conversion complete!\n")
cat("  JSON files saved to:", json_dir, "\n")
