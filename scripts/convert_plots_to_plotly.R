#!/usr/bin/env Rscript

#' Convert ggplot2 objects to Plotly JSON files
#'
#' This script reads .RData/.rds files containing ggplot2 objects
#' (including named lists of ggplot2 objects), converts them to
#' interactive Plotly objects, and exports them as JSON files that
#' can be loaded by JavaScript.
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
appearing_rdata_dir <- file.path(repo_root, "data", "appearing_species_rdata")
reappearing_rdata_dir <- file.path(repo_root, "data", "reappearing_species_rdata")
json_dir <- file.path(repo_root, "data", "indicators_plots_json")

cat("Repository root:", repo_root, "\n")
cat("RData directory:", rdata_dir, "\n")
cat("Appearing RData directory:", appearing_rdata_dir, "\n")
cat("Reappearing RData directory:", reappearing_rdata_dir, "\n")
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
    # Convert ggplot to plotly with focused tooltips
    plotly_obj <- ggplotly(ggplot_obj, tooltip = c("x", "y", "text"))

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


#' Process an R object: if it's a ggplot, convert it; if it's a list,
#' recurse into its elements.  Returns the number of successful conversions.
#'
#' @param obj     An R object (ggplot, list, or other)
#' @param prefix  File-name prefix (without .json)
#' @param out_dir Output directory for JSON files
process_object <- function(obj, prefix, out_dir) {
  converted <- 0L

  if (inherits(obj, "gg") || inherits(obj, "ggplot")) {
    # Direct ggplot object
    json_file <- file.path(out_dir, paste0(prefix, ".json"))
    if (convert_ggplot_to_plotly_json(obj, json_file)) {
      converted <- converted + 1L
    }
  } else if (is.list(obj) && length(obj) > 0) {
    # Named or unnamed list -- iterate over elements
    elem_names <- names(obj)
    for (j in seq_along(obj)) {
      element <- obj[[j]]
      suffix <- if (!is.null(elem_names) && nzchar(elem_names[j])) {
        elem_names[j]
      } else {
        as.character(j)
      }
      child_prefix <- paste0(prefix, "_", suffix)
      converted <- converted + process_object(element, child_prefix, out_dir)
    }
  }
  converted
}


#' Process all RData files in a directory
#'
#' @param src_dir  Directory containing .RData files
#' @param out_dir  Directory where JSON files are written
#' @param label    Human-readable label for progress messages
process_rdata_directory <- function(src_dir, out_dir, label = "plots") {
  if (!dir.exists(src_dir)) {
    cat("Skipping", label, "- directory not found:", src_dir, "\n")
    return(invisible(NULL))
  }

  rdata_files <- list.files(src_dir, pattern = "\\.(RData|rds)$",
                            full.names = TRUE, ignore.case = TRUE)
  if (length(rdata_files) == 0) {
    cat("No RData/rds files found for", label, "in", src_dir, "\n")
    return(invisible(NULL))
  }

  cat(sprintf("\n=== Processing %s (%d file(s)) ===\n", label, length(rdata_files)))

  converted <- 0L
  failed <- 0L

  for (i in seq_along(rdata_files)) {
    rdata_file <- rdata_files[i]
    rdata_basename <- basename(rdata_file)
    cat(sprintf("[%d/%d] %s\n", i, length(rdata_files), rdata_basename))

    env <- new.env()

    tryCatch({
      if (grepl("\\.rds$", rdata_file, ignore.case = TRUE)) {
        obj <- readRDS(rdata_file)
        # Use filename (without extension) as object name
        obj_name <- tools::file_path_sans_ext(rdata_basename)
        assign(obj_name, obj, envir = env)
      } else {
        load(rdata_file, envir = env)
      }

      object_names <- ls(envir = env)
      if (length(object_names) == 0) {
        warning("No objects found in: ", rdata_basename)
        failed <- failed + 1L
        next
      }

      cat(sprintf("  Found %d object(s)\n", length(object_names)))

      for (obj_name in object_names) {
        obj <- get(obj_name, envir = env)
        n <- process_object(obj, obj_name, out_dir)
        converted <- converted + n
        if (n == 0L) failed <- failed + 1L
      }
    }, error = function(e) {
      warning("Failed to load ", rdata_basename, ": ", conditionMessage(e))
      failed <<- failed + 1L
    })

    rm(env)
    gc(verbose = FALSE)
  }

  cat(sprintf("  %s: converted %d, failed %d\n", label, converted, failed))
}


# ---------------------------------------------------------------------------
# Main conversion process
# ---------------------------------------------------------------------------

cat("=== Converting ggplot2 objects to Plotly JSON ===\n\n")

# Create / clean JSON output directory
if (dir.exists(json_dir)) {
  cat("Cleaning existing JSON directory:", json_dir, "\n")
  unlink(json_dir, recursive = TRUE)
}
dir.create(json_dir, recursive = TRUE, showWarnings = FALSE)

start_time <- Sys.time()

# Process indicator plots
process_rdata_directory(rdata_dir, json_dir, "indicator plots")

# Process appearing species plots
process_rdata_directory(appearing_rdata_dir, json_dir, "appearing species plots")

# Process reappearing species plots
process_rdata_directory(reappearing_rdata_dir, json_dir, "reappearing species plots")

elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
cat(sprintf("\n✓ Conversion complete in %.1f seconds\n", elapsed))
cat("  JSON files saved to:", json_dir, "\n")
