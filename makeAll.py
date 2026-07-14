import os
import argparse
from makeYaml import build_codebook_data, extract_file_metadata, check_file_type
from makeCodebook import make_codeBook
import yaml
import logging

logger = logging.getLogger(__name__)

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    parser = argparse.ArgumentParser(
        description="Run the complete pipeline: Generate YAML from source files, then generate the TXT codebook."
    )

    parser.add_argument(
        "-f", "--file", 
        default="Data Files/sfpuf2023_1_fall.csv",
        help="Path to the source data CSV file (default: %(default)s)"
    )
    parser.add_argument(
        "-c", "--catalog", 
        default="2023 Formats/puf_formats_2023.txt",
        help="Path to the txt catalog file (default: %(default)s)"
    )
    parser.add_argument(
        "--format-excel", 
        default="2023 Formats/sfpuf2023_1_fall_formats.xlsx",
        help="Path to the Format Key Excel file (default: %(default)s)"
    )
    parser.add_argument(
        "--label-excel", 
        default="Data Files/sfpuf2023_1_fall_labels.xlsx",
        help="Path to the Label Key Excel file (default: %(default)s)"
    )
    parser.add_argument(
        "--notes-excel", 
        default="2023 PUF Notes/PUFNotes2023.xlsx",
        help="Path to the PUF Notes Excel file (default: %(default)s)"
    )
    parser.add_argument(
        "-o", "--output-dir", 
        default=".",
        help="Directory where BOTH files should be saved (default: current directory)"
    )

    args = parser.parse_args()

    logger.info("Starting pipeline file structure validations...")
    check_file_type(args.file, "data")
    check_file_type(args.catalog, "catalog")
    check_file_type(args.format_excel, "format-excel")
    check_file_type(args.label_excel, "label-excel")
    check_file_type(args.notes_excel, "notes-excel")

    file_year, raw_season, file_season_fmt = extract_file_metadata(args.file)

    logger.info(f"Step 1: Processing source data and generating YAML structure for {raw_season} {file_year}...")
    yaml_data = build_codebook_data(
        file_path=args.file, 
        catalog_path=args.catalog, 
        format_path=args.format_excel, 
        label_path=args.label_excel, 
        notes_path=args.notes_excel, 
        file_year=file_year, 
        file_season_fmt=file_season_fmt
    )

    yaml_filename = f"codebook_{raw_season}_{file_year}.yaml"
    yaml_output_path = os.path.abspath(os.path.join(args.output_dir, yaml_filename))
    
    if os.path.exists(yaml_output_path):
        logger.info(f"Overwriting existing codebook YAML file at: {yaml_output_path}")

    with open(yaml_output_path, "w", encoding="utf-8") as yf:
        yaml.dump(yaml_data, yf, default_flow_style=False, sort_keys=False, allow_unicode=True)
    logger.info(f" -> YAML successfully saved: {yaml_output_path}")

    logger.info("Step 2: Creating the clean text frequency report...")
    report_payload, _ = make_codeBook(yaml_output_path)
    
    txt_filename = f"codeBook_{raw_season}_{file_year}.txt"
    txt_output_path = os.path.abspath(os.path.join(args.output_dir, txt_filename))

    if os.path.exists(txt_output_path):
        logger.info(f"Overwriting existing frequency report TXT file at: {txt_output_path}")
        os.remove(txt_output_path)
        
    with open(txt_output_path, "w", encoding="utf-8") as f:
        f.write(report_payload)
    logger.info(f" -> TXT Report successfully saved: {txt_output_path}")
    
    logger.info("SUCCESS: All files successfully updated and compiled!")

if __name__ == '__main__':
    main()