import argparse
import logging
import os
from datetime import datetime

import yaml

from makeCodebook import make_codeBook
from makeYaml import build_codebook_data, check_file_type

# Initialize module-level logger
logger = logging.getLogger(__name__)


def main():
    """
    Orchestrates the two-stage codebook generation pipeline:
      1. Validates input file extensions and builds the structured codebook YAML data.
      2. Parses the generated YAML data to create a human-readable plain text (.txt) report.
    """
    # -------------------------------------------------------------------------
    # Logging & CLI Configuration
    # -------------------------------------------------------------------------
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description=(
            "Run the complete pipeline: Generate YAML from "
            "source files, then generate the TXT codebook."
        )
    )

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
        help="Directory where BOTH files should be saved (default: current directory)",
    )

    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # 1. Pre-flight Input Validation
    # -------------------------------------------------------------------------
    logger.info("Starting pipeline file structure validations...")
    check_file_type(args.file, "data")
    check_file_type(args.catalog, "catalog")
    check_file_type(args.format_excel, "format-excel")
    check_file_type(args.label_excel, "label-excel")
    check_file_type(args.notes_excel, "notes-excel")

    # -------------------------------------------------------------------------
    # 2. Stage 1: Build & Write YAML Codebook Payload
    # -------------------------------------------------------------------------
    logger.info("Step 1: Processing source data and generating yaml")
    yaml_data = build_codebook_data(
        file_path=args.file,
        catalog_path=args.catalog,
        format_path=args.format_excel,
        label_path=args.label_excel,
        notes_path=args.notes_excel,
    )

    # Resolve YAML output filename (custom string vs. timestamp fallback)
    if args.file_name:
        yaml_output_filename = f"codebook_{args.file_name}.yaml"
    else:
        current_date = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        yaml_output_filename = f"codebook_{current_date}.yaml"

    yaml_output_path = os.path.abspath(
        os.path.join(args.output_dir, yaml_output_filename)
    )

    os.makedirs(args.output_dir, exist_ok=True)

    if os.path.exists(yaml_output_path):
        logger.info(f"Overwriting existing codebook YAML file at: {yaml_output_path}")

    # Write dictionary to YAML using clean block formatting
    with open(yaml_output_path, "w", encoding="utf-8") as yf:
        yaml.dump(
            yaml_data,
            yf,
            default_flow_style=False,
            sort_keys=False,
            allow_unicode=True,
        )
    logger.info(f" -> YAML successfully saved: {yaml_output_path}")

    # -------------------------------------------------------------------------
    # 3. Stage 2: Build & Write Text Frequency Report
    # -------------------------------------------------------------------------
    logger.info("Step 2: Creating the clean text frequency report...")
    report_payload = make_codeBook(yaml_output_path)

    base_name = os.path.splitext(yaml_output_filename)[0]
    txt_output_path = os.path.abspath(os.path.join(args.output_dir, f"{base_name}.txt"))

    if os.path.exists(txt_output_path):
        logger.info(
            f"Overwriting existing frequency report TXT file at: {txt_output_path}"
        )
        os.remove(txt_output_path)

    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write(report_payload)
    logger.info(f" -> TXT Report successfully saved: {txt_output_path}")

    logger.info("SUCCESS: All files successfully updated and compiled!")


if __name__ == "__main__":
    main()
