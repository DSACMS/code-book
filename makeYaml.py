import argparse
import logging
import os
import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import yaml

logger = logging.getLogger(__name__)


def check_file_type(file_path: str, file_category: str) -> str:
    """Validates that a file's extension matches the permitted formats for its pipeline category.

    Acts as an early fail-fast guard before launching resource-heavy data ingestion jobs.

    Args:
        file_path: Relative or absolute path to the input file.
        file_category: Pipeline domain category (case-insensitive, whitespace-tolerant).

    Returns:
        str: The matched file extension without the leading dot (e.g., 'csv', 'xlsx').

    Raises:
        ValueError: If `file_category` is unrecognized or `file_path` lacks a valid extension.
    """
    path = Path(file_path)

    # Path.suffix returns lowercase dot extension (e.g., '.csv')
    # Note: For multi-part extensions like '.tar.gz', Path.suffix only captures '.gz'
    extension = path.suffix.lower()

    # Domain registry mapping categories to permitted extensions
    valid_extensions = {
        "data": [".csv"],
        "catalog": [".txt"],
        "format-excel": [".xlsx", ".xls"],
        "label-excel": [".xlsx", ".xls"],
        "notes-excel": [".xlsx", ".xls"],
    }

    # Normalize category input
    category = file_category.lower().strip()

    if category not in valid_extensions:
        raise ValueError(
            f"Unknown file category: '{file_category}'. "
            f"Valid categories are {list(valid_extensions.keys())}"
        )

    allowed = valid_extensions[category]

    if extension in allowed:
        return extension.lstrip(".")

    # Construct human-readable expectation list (e.g., '.xlsx or .xls')
    allowed_str = " or ".join(allowed)
    raise ValueError(
        f"Unsupported file type for {category}: '{extension}'. Expected {allowed_str}."
    )


def convert(val: object) -> int | float | str:
    """
    Standardizes input data types into int, float, or str.

    Order of operations:
    1. Pass-through existing floats and ints directly.
    2. Try parsing decimal strings directly as float.
    3. Try parsing standard integer strings.
    4. Fall back to float for non-period floats (e.g., '1e-5', 'inf').
    5. Fall back to str for any non-numeric text strings.
    """
    if val is None or pd.isna(val):
        return "."

    if isinstance(val, (int, float)):
        return val

    try:
        if isinstance(val, str) and "." in val:
            return float(val)

        return int(val)

    except ValueError:
        try:
            return float(val)

        except ValueError:
            return str(val)


def read_data(file_path: str) -> pd.DataFrame:
    """
    Ingests the raw survey dataset and applies global formatting.

    Replaces missing values (NaN) with a period ('.') standard sas missing marker,
    and applies `convert()` across all values to standardize numeric strings and
    integers into floats.

    Parameters
    ----------
    file_path : str
        Path to the source CSV file.

    Returns
    -------
    pd.DataFrame
        A DataFrame with standardized string, float, and missing representation.
    """
    # Load dataset with low_memory=False to prevent mixed-type chunk warnings on large files;
    # replace null values with SAS-style missing markers ('.')
    df = pd.read_csv(file_path, low_memory=False).fillna(".")

    # Apply type conversion across every element in the DataFrame
    for col in df.columns:
        df[col] = df[col].map(lambda val: convert(val))

    return df


def parse_catalog(catalog_path: str) -> dict[str, dict[str, str]]:
    """Parses SAS style value catalog files (.txt) into a nested dictionary.

    Format structures inside the catalog file follow this pattern:
        value FORMAT_NAME
            code = "Label"
            code2 = "Prefix: Description";

    Args:
        catalog_path: Path to the plain text catalog configuration file.

    Returns:
        dict: A nested mapping structured as:
            {
                "FORMAT_NAME": {
                    "code_key": "Cleaned Label Text"
                }
            }

    Raises:
        FileNotFoundError: If `catalog_path` cannot be located on disk.
    """
    format_dict = {}
    current_value = None

    # Regex breakdown:
    # ^value\s+(\w+) -> Matches 'value' followed by format block identifier
    VALUE_HEADER_RE = re.compile(r"^value\s+(\w+)", re.IGNORECASE)

    # Regex breakdown:
    # ^([\w.-]+)     -> Key code (letters, digits, underscores, dots, hyphens)
    # \s*=\s*        -> Equals sign surrounded by optional whitespace
    # "([^"]*)"      -> Quoted label text
    # \s*;?$         -> Optional trailing semicolon at line end
    MAPPING_RE = re.compile(r"^([\w.-]+)\s*=\s*\"([^\"]*)\"\s*;?$")

    try:
        with open(catalog_path, encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                # Ignore blank lines and comments
                if not line or line.startswith("//") or line.startswith("#"):
                    continue

                # Check for new format header (e.g. 'value YESNOFMT')
                value_match = VALUE_HEADER_RE.match(line)
                if value_match:
                    current_value = value_match.group(1).upper()
                    continue

                # Check for key-value pair inside an active format block
                mapping_match = MAPPING_RE.match(line)
                if mapping_match and current_value:
                    key_code = mapping_match.group(1).strip()
                    label_text = mapping_match.group(2)

                    # Strip metadata prefixes like 'Category A: Real Description' -> 'Real Description'
                    if ":" in label_text:
                        label_text = label_text.split(":", 1)[1].strip()

                    if current_value not in format_dict:
                        format_dict[current_value] = {}

                    format_dict[current_value][key_code] = label_text

    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Configuration Error: The required catalog file at '{catalog_path}' "
            "was not found. Please check the file path and try again."
        ) from e

    return format_dict


def build_codebook_data(
    file_path: str,
    catalog_path: str,
    format_path: str,
    label_path: str,
    notes_path: str,
) -> dict:
    """
    Builds a structured dictionary payload suitable for YAML codebook export.

    Combines raw data with variable metadata, format catalogs, variable labels,
    and supplementary survey notes/question numbers.

    Parameters
    ----------
    file_path : str
        Path to the primary raw survey dataset (read via `read_data`).
    catalog_path : str
        Path to the SAS format catalog text file.
    format_path : str
        Path to the Excel file mapping variable names to format names.
    label_path : str
        Path to the Excel file mapping variable names to variable labels.
    notes_path : str
        Path to the Excel file containing question numbers and footnotes.

    Returns
    -------
    dict
        A nested dictionary mapping each column name to its codebook metadata:
        - `format` (str): Uppercase format name applied to the variable.
        - `description` (str): Human-readable variable label.
        - `value_distributions` (list[dict]): List of `{"code", "label", "frequency"}`.
        - `qnbr` (list[str], optional): Cleaned question numbers associated with variable.
        - `notes`, `notes2`, `notes3` (str, optional): Additional footnotes.

    Raises
    ------
    KeyError
        If a survey dataset column is missing from `format_key` or `label_key`,
        or if a specified format name is missing from the parsed catalog.
    """
    # -------------------------------------------------------------------------
    # 1. Load Raw Data & Metadata Lookup Tables
    # -------------------------------------------------------------------------
    df = read_data(file_path)

    # Format key: maps variable names to SAS format names (strips trailing dots like 'YESNO.')
    format_key = pd.read_excel(format_path, engine="openpyxl").set_index("Variable")
    format_key["Format"] = (
        format_key["Format"].astype(str).str.replace(".", "", regex=False)
    )

    # Catalog: parsed dict mapping format names to value-label dicts
    catalog = parse_catalog(catalog_path)

    # Label key: maps variable names to descriptive text labels
    label_key = pd.read_excel(label_path, engine="openpyxl").set_index("Variable")

    # Notes sheet: contains question numbers (qnbr) and multi-line footnotes
    df_notes = pd.read_excel(notes_path, engine="openpyxl")

    yaml_data = {}

    # -------------------------------------------------------------------------
    # 2. Process Metadata & Frequency Distributions Column-by-Column
    # -------------------------------------------------------------------------
    for col in df.columns:
        # Validate format lookup mapping
        if col not in format_key.index:
            raise KeyError(f"Column '{col}' not found in format_key DataFrame.")

        fmt_name = str(format_key.at[col, "Format"]).upper().strip()

        # Validate format exists in catalog before probing entries
        if fmt_name not in catalog:
            raise KeyError(f"Format '{fmt_name}' not found in the catalog.")

        # Continuous / ID variable handling: aggregate all numeric values into a single "LOW-HIGH" category
        if any(key == "LOW-HIGH" for key in catalog[fmt_name]):
            num_or_nan = pd.to_numeric(df[col], errors="coerce")
            is_digit = num_or_nan.notna()
            df[col] = df[col].astype(str)
            df.loc[is_digit, col] = "LOW-HIGH"

        # Validate variable label mapping
        if col not in label_key.index:
            raise KeyError(f"Column '{col}' not found in label_key DataFrame.")

        var_label = label_key.at[col, "Label"]

        # Base dictionary entry for the variable
        var_entry = {
            "format": fmt_name,
            "description": var_label,
            "value_distributions": [],
        }

        # ---------------------------------------------------------------------
        # 3. Calculate Frequencies Against Catalog Codes
        # ---------------------------------------------------------------------
        val_counts = df[col].value_counts()
        inner_dict = catalog[fmt_name]

        for key, label in sorted(inner_dict.items()):
            # Normalize catalog keys (remove dots from special codes like '.R', except lone '.')
            if key != "." and "." in key:
                key = key.replace(".", "")
            else:
                key = convert(key)

            label = convert(label)
            freq = int(val_counts.get(key, 0))

            # Record non-zero value frequencies
            if freq > 0:
                var_entry["value_distributions"].append(
                    {"code": key, "label": label, "frequency": freq}
                )

        # Log warning/debug if no observed values matched any catalog codes
        if not var_entry["value_distributions"]:
            logger.debug(f"value distributions missing for variable {col}")

        # ---------------------------------------------------------------------
        # 4. Attach Question Numbers & Footnotes
        # ---------------------------------------------------------------------
        matched_notes = df_notes[df_notes["var_nm"] == col]

        if not matched_notes.empty:
            for _, row in matched_notes.iterrows():
                for note_col in ["qnbr", "notes", "notes2", "notes3"]:
                    note_content = row.get(note_col)
                    if pd.notna(note_content) and str(note_content).strip() != "":
                        cleaned_val = str(note_content).strip()

                        # Process comma-delimited question numbers into a clean list
                        if note_col == "qnbr":
                            questions = [
                                q.strip() for q in cleaned_val.split(",") if q.strip()
                            ]
                            var_entry[note_col] = questions
                        else:
                            var_entry[note_col] = cleaned_val

        yaml_data[col] = var_entry

    return yaml_data


def main() -> None:
    """
    Command-Line Interface (CLI) entrypoint for generating codebook YAML files.

    Parses command-line arguments, validates input file paths, invokes dataset
    processing, and exports the resulting structured codebook to disk as a YAML file.
    """
    # -------------------------------------------------------------------------
    # 1. Configure Logging & CLI Argument Parser
    # -------------------------------------------------------------------------
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description=(
            "Generate a structured Codebook YAML file from CSV data and Excel lookups."
        )
    )

    # Dataset & Catalog file inputs
    parser.add_argument(
        "-f",
        "--file",
        default="sample1/sfpuf2023_1_fall.csv",
        help="Path to the source data CSV file (default: %(default)s)",
    )
    parser.add_argument(
        "-c",
        "--catalog",
        default="sample1/puf_formats_2023.txt",
        help="Path to the txt catalog file (default: %(default)s)",
    )

    # Excel Key lookup inputs
    parser.add_argument(
        "--format-excel",
        default="sample1/sfpuf2023_1_fall_formats.xlsx",
        help="Path to the Format Key Excel file (default: %(default)s)",
    )
    parser.add_argument(
        "--label-excel",
        default="sample1/sfpuf2023_1_fall_labels.xlsx",
        help="Path to the Label Key Excel file (default: %(default)s)",
    )
    parser.add_argument(
        "--notes-excel",
        default="sample1/PUFNotes2023.xlsx",
        help="Path to the Notes Excel file (default: %(default)s)",
    )

    # Output naming & destination options
    parser.add_argument(
        "-s",
        "--file-name",
        default=None,
        help="Optional name associated with the dataset (e.g., PUFWINTER_2023)",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        help=(
            "Directory where the output YAML file should be "
            "saved (default: current directory)"
        ),
    )

    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # 2. Input Structure Validation
    # -------------------------------------------------------------------------
    logger.info("Validating file structures...")
    check_file_type(args.file, "data")
    check_file_type(args.catalog, "catalog")
    check_file_type(args.format_excel, "format-excel")
    check_file_type(args.label_excel, "label-excel")
    check_file_type(args.notes_excel, "notes-excel")

    # -------------------------------------------------------------------------
    # 3. Build Codebook Payload
    # -------------------------------------------------------------------------
    logger.info("Processing data and building codebook yaml file")
    yaml_data = build_codebook_data(
        file_path=args.file,
        catalog_path=args.catalog,
        format_path=args.format_excel,
        label_path=args.label_excel,
        notes_path=args.notes_excel,
    )

    # -------------------------------------------------------------------------
    # 4. Resolve Output Path & Export YAML
    # -------------------------------------------------------------------------
    # Construct filename based on user-provided dataset tag or timestamp
    if args.file_name:
        yaml_output_filename = f"codebook_{args.file_name}.yaml"
    else:
        current_date = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        yaml_output_filename = f"codebook_{current_date}.yaml"

    yaml_output_path = os.path.abspath(
        os.path.join(args.output_dir, yaml_output_filename)
    )

    # Ensure output directory exists prior to writing
    os.makedirs(args.output_dir, exist_ok=True)

    if os.path.exists(yaml_output_path):
        logger.info(f"Overwriting existing codebook file at: {yaml_output_path}")

    logger.info("Writing results to disk...")
    with open(yaml_output_path, "w", encoding="utf-8") as yf:
        yaml.dump(
            yaml_data,
            yf,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )

    logger.info(f"Clean variable codebook built successfully: {yaml_output_path}")


if __name__ == "__main__":
    main()
