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


# Mapping from descriptive indicator names to numeric indices used by the
# dashboard JavaScript.
INDICATOR_INDEX <- c(
  "number of occurrences"          = "1",
  "number of grid cells (10x10km)" = "2"
)


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
      # Map known indicator names to numeric indices expected by the dashboard
      if (suffix %in% names(INDICATOR_INDEX)) {
        suffix <- INDICATOR_INDEX[[suffix]]
      }
      child_prefix <- paste0(prefix, "_", suffix)
      converted <- converted + process_object(element, child_prefix, out_dir)
    }
  }
  converted
}


#' Extract the LME name from an indicator-plot RData filename.
#'
#' Indicator files: indicators_plots_ggplot2_{lme_name}_chunk_{n}.RData
#' Appearing files:  appearing_species_plots_ggplot2_lme_{lme_name}.RData
#' Reappearing files: reappearing_species_plots_ggplot2_lme_{lme_name}.RData
#'
#' @param basename Filename without directory
#' @return The LME name, or NULL if pattern does not match
extract_lme_name <- function(basename) {
  sans <- tools::file_path_sans_ext(basename)

  # Indicator plots: indicators_plots_ggplot2_{lme_name}_chunk_{n}
  m <- regmatches(sans, regexec("^indicators_plots_ggplot2_(.+)_chunk_\\d+$", sans, perl = TRUE))[[1]]
  if (length(m) == 2) return(m[2])

  # Appearing / reappearing: {prefix}_lme_{lme_name}
  m <- regmatches(sans, regexec("^(?:appearing|reappearing)_species_plots_ggplot2_lme_(.+)$", sans, perl = TRUE))[[1]]
  if (length(m) == 2) return(m[2])

  NULL
}


#' Build the expected prefix for a loaded object based on the source filename
#' and the category of plots being processed.
#'
#' For indicator plots the dashboard expects:
#'   lme_{lme_name}_species_{species_key}_{1|2}.json
#'
#' For appearing/reappearing species plots:
#'   {category}_lme_{lme_name}_species_{species_key}_{1|2}.json
#'   where category is e.g. "appearing_species_plots_ggplot2"
#'
#' @param rdata_basename  Filename of the source RData file (without path)
#' @param obj_name        Name of the R object as loaded from the file
#' @param category        One of "indicators", "appearing", "reappearing"
#' @return A prefix string to use when calling process_object, or NULL to use
#'   the default (obj_name) when the pattern is not recognised.
build_prefix <- function(rdata_basename, obj_name, category) {
  lme_name <- extract_lme_name(rdata_basename)
  if (is.null(lme_name)) return(NULL)

  if (category == "indicators") {
    # The loaded object is named "chunk" and contains species-keyed sub-lists.
    # We want the prefix to expand to: lme_{lme}_species_{key}_{1|2}
    return(paste0("lme_", lme_name, "_species"))
  }

  if (category == "appearing") {
    return(paste0("appearing_species_plots_ggplot2_lme_", lme_name, "_species"))
  }

  if (category == "reappearing") {
    return(paste0("reappearing_species_plots_ggplot2_lme_", lme_name, "_species"))
  }

  NULL
}


#' Process all RData files in a directory
#'
#' @param src_dir   Directory containing .RData files
#' @param out_dir   Directory where JSON files are written
#' @param label     Human-readable label for progress messages
#' @param category  One of "indicators", "appearing", "reappearing" (used to
#'                  derive the correct output filename pattern)
process_rdata_directory <- function(src_dir, out_dir, label = "plots",
                                    category = NULL) {
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

        # Determine the prefix: use the category-aware builder when available,
        # falling back to the raw object name for backwards compatibility.
        prefix <- if (!is.null(category)) {
          bp <- build_prefix(rdata_basename, obj_name, category)
          if (!is.null(bp)) bp else obj_name
        } else {
          obj_name
        }

        n <- process_object(obj, prefix, out_dir)
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
process_rdata_directory(rdata_dir, json_dir, "indicator plots",
                        category = "indicators")

# Process appearing species plots
process_rdata_directory(appearing_rdata_dir, json_dir, "appearing species plots",
                        category = "appearing")

# Process reappearing species plots
process_rdata_directory(reappearing_rdata_dir, json_dir, "reappearing species plots",
                        category = "reappearing")

elapsed <- as.numeric(difftime(Sys.time(), start_time, units = "secs"))
cat(sprintf("\n✓ Conversion complete in %.1f seconds\n", elapsed))
cat("  JSON files saved to:", json_dir, "\n")
