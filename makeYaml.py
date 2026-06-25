import pandas as pd
import pyreadstat
import os 
import re
import yaml
import argparse

def extract_file_metadata(file_path):
    """
    Extracts the year, raw season, and formatted season strings from the filename.
    """
    filename = os.path.basename(file_path)
    pattern = r"sfpuf(\d{4})_(\d+)_([a-zA-Z]+)\.sas7bdat"
    match = re.search(pattern, filename)

    if match:
        file_year = int(match.group(1))   
        raw_season = match.group(3).upper() # e.g., FALL
        file_season_fmt = f"PUF_{raw_season}" 
        return file_year, raw_season, file_season_fmt
    else:
        raise ValueError("Could not extract year and season from the file name format.")

def build_codebook_data(file_path, catalog_path, excel_path, file_year, file_season_fmt):
    """
    Processes the dataframes and metadata to compile the codebook dictionary structure.
    """
    df, meta = pyreadstat.read_sas7bdat(file_path, user_missing=True)
    _, format_key = pyreadstat.read_sas7bcat(catalog_path)
    df_notes = pd.read_excel(excel_path, engine="openpyxl")

    formats = meta.variable_to_label.copy()
    descriptions = meta.column_names_to_labels.copy()

    df = df.fillna('.')

    for variable, format_name in formats.items():
        if format_name == 'CONTIN':
            num_or_nan = pd.to_numeric(df[variable], errors='coerce')
            is_digit = num_or_nan.notna()
            df[variable] = df[variable].astype(str)
            df.loc[is_digit, variable] = 'LOW-HIGH'

    df['PUF_ID'] = 'LOW-HIGH'

    yaml_data = {}

    for col in df.columns:
        fmt_name = formats.get(col, None)
        var_label = descriptions.get(col, None)
        
        var_entry = {
            "format": fmt_name,
            "description": var_label,
            "value_distributions": []
        }
        
        if fmt_name in format_key.value_labels:
            inner_dict = format_key.value_labels[fmt_name]
            
            for key, label in inner_dict.items():
                if key == -1.7976931348623157e+308:
                    key_display = "LOW-HIGH"
                    freq = int((df[col] == "LOW-HIGH").sum())

                elif pd.isna(key):
                    key_display = '.'
                    freq = int((df[col] == '.').sum())

                else:
                    key_display = str(key)
                    freq = int((df[col] == key).sum())
                
                if freq > 0:
                    clean_label = label.split(':', 1)[1].strip() if ':' in label else label
                    
                    var_entry["value_distributions"].append({
                        "code": key_display,
                        "label": clean_label,
                        "frequency": freq
                    })
                    
        matched_notes = df_notes[
            (df_notes['var_nm'] == col) & 
            (df_notes['file'] == file_season_fmt) & 
            ((df_notes['yr'] == file_year) | (df_notes['yr'].isna()))
        ]
        
        if not matched_notes.empty:
            for _, row in matched_notes.iterrows():
                for note_col in ['notes', 'notes2', 'notes3']:
                    note_content = row.get(note_col)
                    if pd.notna(note_content) and str(note_content).strip() != "":
                        var_entry[note_col] = str(note_content).strip()    
        
        yaml_data[col] = var_entry
        
    return yaml_data

def main():
    # 1. Set up the argument parser
    parser = argparse.ArgumentParser(
        description="Generate a structured Codebook YAML file from SAS datasets and formats."
    )

    # 2. Define the command-line arguments (with your original paths as defaults)
    parser.add_argument(
        "-f", "--file", 
        help="Path to the source SAS7BDAT file (default: %(default)s)"
    )
    parser.add_argument(
        "-c", "--catalog", 
        help="Path to the SAS7BCAT catalog file (default: %(default)s)"
    )
    parser.add_argument(
        "-e", "--excel", 
        help="Path to the PUF Notes Excel file (default: %(default)s)"
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=".",
        help="Directory where the output YAML file should be saved (default: current directory)"
    )

    # 3. Parse the arguments from the command line
    args = parser.parse_args()

    # Extract naming parameters dynamically using parsed arguments
    file_year, raw_season, file_season_fmt = extract_file_metadata(args.file)

    # Build the core structured dictionary payload
    yaml_data = build_codebook_data(
        args.file, args.catalog, args.excel, 
        file_year, file_season_fmt
    )

    # Format target output file path
    yaml_output_filename = f"codeBook{raw_season}{file_year}.yaml"
    yaml_output_path = os.path.abspath(os.path.join(args.output_dir, yaml_output_filename))

    # Save the codebook data to the YAML file
    with open(yaml_output_path, "w", encoding="utf-8") as yf:
        yaml.dump(yaml_data, yf, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"Clean variable codebook built successfully: {yaml_output_path}")

if __name__ == '__main__':
    main()