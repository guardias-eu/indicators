#!/usr/bin/env Rscript

#' Convert ggplot2 objects to Plotly JSON files
#'
#' This script reads .RData files containing ggplot2 objects,
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
rdata_dir <- file.path(repo_root, "data", "indicators_plots_rdata")
json_dir <- file.path(repo_root, "data", "indicators_plots_json")

cat("Repository root:", repo_root, "\n")
cat("RData directory:", rdata_dir, "\n")
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

# Check if RData directory exists
if (!dir.exists(rdata_dir)) {
  stop("RData directory not found: ", rdata_dir, "\n",
       "Please run download_emtrends_data.py first to download the RData files.")
}

# Create JSON output directory
if (dir.exists(json_dir)) {
  cat("Cleaning existing JSON directory:", json_dir, "\n")
  unlink(json_dir, recursive = TRUE)
}
dir.create(json_dir, recursive = TRUE, showWarnings = FALSE)

# Get all RData files
rdata_files <- list.files(rdata_dir, pattern = "\\.RData$", full.names = TRUE)

if (length(rdata_files) == 0) {
  stop("No RData files found in: ", rdata_dir, "\n",
       "Please run download_emtrends_data.py first to download the RData files.")
}

cat("Found", length(rdata_files), "RData files to process\n\n")

# Track conversion statistics
converted <- 0
failed <- 0
start_time <- Sys.time()

# Process each RData file
for (i in seq_along(rdata_files)) {
  rdata_file <- rdata_files[i]
  rdata_basename <- basename(rdata_file)
  
  # Progress update
  cat(sprintf("[%d/%d] Processing %s\n", i, length(rdata_files), rdata_basename))
  
  # Load the RData file into a new environment
  # This prevents polluting the global environment
  env <- new.env()
  
  tryCatch({
    load(rdata_file, envir = env)
    
    # Get all objects in the loaded environment
    object_names <- ls(envir = env)
    
    if (length(object_names) == 0) {
      warning("No objects found in RData file: ", rdata_basename)
      failed <- failed + 1
      next
    }
    
    cat(sprintf("  Found %d object(s) in RData file\n", length(object_names)))
    
    # Process each object
    for (obj_name in object_names) {
      obj <- get(obj_name, envir = env)
      
      # Check if it's a ggplot object
      if (!inherits(obj, "gg") && !inherits(obj, "ggplot")) {
        cat(sprintf("  Skipping non-ggplot object: %s\n", obj_name))
        next
      }
      
      # Build output filename: obj_name.json
      json_file <- file.path(json_dir, paste0(obj_name, ".json"))
      
      # Convert to Plotly JSON
      if (convert_ggplot_to_plotly_json(obj, json_file)) {
        converted <- converted + 1
      } else {
        failed <- failed + 1
      }
    }
    
  }, error = function(e) {
    warning("Failed to load RData file ", rdata_basename, ": ", conditionMessage(e))
    failed <- failed + 1
  })
  
  # Clean up environment
  rm(env)
  gc(verbose = FALSE)
  
  # Progress report every 5 files
  if (i %% 5 == 0 || i == length(rdata_files)) {
    elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
    rate <- i / elapsed
    remaining <- (length(rdata_files) - i) / rate
    cat(sprintf("  Progress: %d/%d RData files (converted: %d plots, failed: %d, ~%.0fs remaining)\n",
                i, length(rdata_files), converted, failed, remaining))
  }
}

# Final statistics
end_time <- Sys.time()
elapsed <- as.numeric(difftime(end_time, start_time, units = "secs"))

cat("\n=== Conversion complete ===\n")
cat(sprintf("  Converted: %d plots\n", converted))
cat(sprintf("  Failed: %d plots\n", failed))
cat(sprintf("  Time elapsed: %.1f seconds\n", elapsed))

if (failed > 0) {
  cat("\n⚠ Warning:", failed, "plots failed to convert.\n")
  cat("  Check warnings above for details.\n")
}

cat("\n✓ Conversion complete!\n")
cat("  JSON files saved to:", json_dir, "\n")
