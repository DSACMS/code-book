import pandas as pd
import os 
import re
import yaml
import argparse
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def check_file_type(file_path, file_category):
    """Validates that the provided file path matches the permitted extensions for its pipeline category.

    Ensures early structural failure before kicking off heavy data ingestion.
    """
    path = Path(file_path)
    extension = path.suffix.lower()
    
    valid_extensions = {
        "data": [".csv"],
        "catalog": [".txt"],
        "format-excel": [".xlsx", ".xls"],
        "label-excel": [".xlsx", ".xls"],
        "notes-excel": [".xlsx", ".xls"]
    }
    
    category = file_category.lower().strip()
    
    if category not in valid_extensions:
        raise ValueError(f"Unknown file category: '{file_category}'. Valid categories are {list(valid_extensions.keys())}")
        
    allowed = valid_extensions[category]
    
    if extension in allowed:
        return extension.lstrip('.') 
    else:
        allowed_str = " or ".join(allowed)
        raise ValueError(f"Unsupported file type for {file_category}: '{extension}'. Expected {allowed_str}.")

def convert(val):
    """Evaluates to true if the input is either a numeric string or integer.
    Used for standardizing numeric input data types to float."""
    try:
        val = int(val)
        return val
    except ValueError:
        try:
            val = float(val)
            return val
        except ValueError:
            return str(val)

def read_data(file_path):
    """Ingests the response source file.
    Fills missing values with periods, and turns any numeric strings,
    or integers into floats.
    """
    df = pd.read_csv(file_path, low_memory=False).fillna('.')
    for col in df.columns:
        df[col] = df[col].map(lambda val: convert(val))
    return df

def parse_puf_catalog(catalog_path):
    """Parses the .txt PUF Catalog, containing each format type, in addition to the 
    codes and definitons for the codes pertaining to a specific format. Stores this
    information as a nested dictionary.
    """
    format_dict = {}
    current_value = None
    
    try:
        with open(catalog_path, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                value_match = re.match(r"^value\s+(\w+)", line, re.IGNORECASE)
                
                if value_match:
                    current_value = value_match.group(1).upper()
                    continue

                mapping_match = re.match(r"^([\w\.\-]+)\s*=\s*\"([^\"]*)\"\s*;?$", line)

                if mapping_match and current_value:
                    key_code = mapping_match.group(1).strip()
                    label_text = mapping_match.group(2)
                    
                    if ":" in label_text:
                        label_text = label_text.split(":", 1)[1].strip()

                    if current_value not in format_dict:
                        format_dict[current_value] = {}

                    format_dict[current_value][key_code] = label_text

    except FileNotFoundError as e:
        raise FileNotFoundError(
            f"Configuration Error: The required catalog file at '{catalog_path}' was not found. "
            "Please check the file path and try again."
        ) from e

    return format_dict

def extract_file_metadata(file_path):
    """
    Extracts the year, raw season, and formatted season strings from the filename.
    """
    filename = os.path.basename(file_path)
    pattern = r"sfpuf(\d{4})_(\d+)_([a-zA-Z]+)\.csv"
    match = re.search(pattern, filename)

    if match:
        file_year = int(match.group(1))   
        raw_season = match.group(3).upper() 
        file_season_fmt = f"PUF_{raw_season}" 
        return file_year, raw_season, file_season_fmt
    else:
        raise ValueError("Could not extract year and season from the file name format.")

def build_codebook_data(file_path, catalog_path, format_path, label_path, notes_path, file_year, file_season_fmt):
    """
    Processes the response source file, bringing in metadata for variable labels, variable formats, 
    and variable notes. Combines all of this into a structured YAML payload codebook. 
    """
    df = read_data(file_path) 
    
    format_key = pd.read_excel(format_path, engine="openpyxl").set_index('Variable')
    format_key['Format'] = format_key['Format'].astype(str).str.replace('.', '', regex=False)

    puf_catalog = parse_puf_catalog(catalog_path)

    label_key = pd.read_excel(label_path, engine="openpyxl").set_index('Variable')
    
    df_notes = pd.read_excel(notes_path, engine="openpyxl")

    if "PUF_ID" in df.columns:
        df['PUF_ID'] = 'LOW-HIGH'

    yaml_data = {}

    for col in df.columns:
        if col not in format_key.index:
            raise KeyError(f"Column '{col}' not found in format_key DataFrame.")
        else:
            fmt_name = str(format_key.at[col, 'Format']).upper().strip()
        
        if fmt_name == 'CONTIN':
            num_or_nan = pd.to_numeric(df[col], errors='coerce')
            is_digit = num_or_nan.notna()
            df[col] = df[col].astype(str)
            df.loc[is_digit, col] = 'LOW-HIGH'
            
        if col not in label_key.index:
            raise KeyError(f"Column '{col}' not found in label_key DataFrame.")
        else:
            var_label = label_key.at[col, 'Label']

        var_entry = {
            "format": fmt_name,
            "description": var_label,
            "value_distributions": []
        }

        val_counts = df[col].value_counts()
        
        if puf_catalog and fmt_name in puf_catalog:
            inner_dict = puf_catalog[fmt_name]
            
            for key, label in sorted(inner_dict.items()):
                if key != '.' and '.' in key:
                    key = key.replace('.', '')
                else:
                    key = convert(key)
                
                label = convert(label)
                
                freq = int(val_counts.get(key, 0))
                
                if freq > 0:                    
                    var_entry["value_distributions"].append({
                        "code": key,
                        "label": label,
                        "frequency": freq
                    })
        else:
            raise KeyError(f"Format '{fmt_name}' not found in the PUF catalog.")
                    
        matched_notes = df_notes[
            (df_notes['var_nm'] == col) & 
            (df_notes['file'] == file_season_fmt) & 
            ((df_notes['yr'] == file_year) | (df_notes['yr'].isna()))
        ]
        
        if not matched_notes.empty:
            for _, row in matched_notes.iterrows():
                for note_col in ['qnbr', 'notes', 'notes2', 'notes3']:
                    note_content = row.get(note_col)
                    if pd.notna(note_content) and str(note_content).strip() != "":
                        if note_col == 'qnbr':
                            note_col = "question_numbers"
                            questions = [q.strip() for q in note_content.split(',')]
                            var_entry[note_col] = questions   
                        else:
                            var_entry[note_col] = str(note_content).strip()    
                        
        yaml_data[col] = var_entry
        
    return yaml_data

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    parser = argparse.ArgumentParser(
        description="Generate a structured Codebook YAML file from CSV data and Excel lookups."
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
        help="Directory where the output YAML file should be saved (default: current directory)"
    )

    args = parser.parse_args()

    logger.info("Validating file structures...")
    check_file_type(args.file, "data")
    check_file_type(args.catalog, "catalog")
    check_file_type(args.format_excel, "format-excel")
    check_file_type(args.label_excel, "label-excel")
    check_file_type(args.notes_excel, "notes-excel")

    logger.info("Extracting file metadata...")
    file_year, raw_season, file_season_fmt = extract_file_metadata(args.file)

    logger.info(f"Processing data and building codebook for {raw_season} {file_year}...")
    yaml_data = build_codebook_data(
        file_path=args.file, 
        catalog_path=args.catalog, 
        format_path=args.format_excel, 
        label_path=args.label_excel, 
        notes_path=args.notes_excel, 
        file_year=file_year, 
        file_season_fmt=file_season_fmt
    )

    yaml_output_filename = f"codebook_{raw_season}_{file_year}.yaml"
    yaml_output_path = os.path.abspath(os.path.join(args.output_dir, yaml_output_filename))

    if os.path.exists(yaml_output_path):
        logger.info(f"Overwriting existing codebook file at: {yaml_output_path}")

    logger.info("Writing results to disk...")
    with open(yaml_output_path, "w", encoding="utf-8") as yf:
        yaml.dump(yaml_data, yf, default_flow_style=False, sort_keys=False, allow_unicode=True)

    logger.info(f"Clean variable codebook built successfully: {yaml_output_path}")
    
if __name__ == '__main__':
    main()