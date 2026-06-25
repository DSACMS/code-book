import yaml
import os
import re
import argparse

def make_codeBook(yaml_path):
    """
    Reads a variable codebook YAML file and writes a plain text (.txt) report.
    The script automatically creates the output filename using the season and year.
    """
    # Stop if the input YAML file cannot be found
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"Could not find codebook file at '{yaml_path}'")

    # Get the filename from the path to look for the season and year
    filename = os.path.basename(yaml_path)
    
    # Regex look for 'codeBook' followed by letters (season) and numbers (year)
    pattern = r"codeBook([a-zA-Z]+)(\d+)\.yaml"
    match = re.search(pattern, filename)
    
    if match:
        season = match.group(1)  # Extracts the season (e.g., 'FALL')
        year = match.group(2)    # Extracts the year (e.g., '2023')
    else:
        season, year = None, None

    # Open and read the YAML data
    with open(yaml_path, "r", encoding="utf-8") as yf:
        # SafeLoader reads the file safely as standard Python dictionaries and lists
        codebook = yaml.load(yf, Loader=yaml.SafeLoader)

    # Stop if the file is blank or has invalid content
    if not codebook:
        raise ValueError(f"The codebook file at '{yaml_path}' is empty or could not be parsed.")

    # Build the report content in memory using a list of lines
    report_lines = []
    
    # Write the main document title banner
    report_lines.append("=" * 70)
    report_lines.append(f"{'PUBLIC USE FILE (PUF) VARIABLE FREQUENCY REPORT':^70}")
    report_lines.append("=" * 70 + "\n")

    # Loop through every variable item stored in the YAML data
    for col, info in codebook.items():
        # Get the format and description, using a space if they are missing
        fmt_name = info.get("format", " ")
        var_label = info.get("description", " ")
        
        # Write out the variable name, format, and description headings
        report_lines.append(f"Variable Name: {col} (Format: {fmt_name})")
        report_lines.append(f"Description:   {var_label}")
        report_lines.append("-" * 65)
        report_lines.append(f"{'Code':<10} | {'Value Label':<35} | {'Frequency':<12}")
        report_lines.append("-" * 65)
        
        # Get the list of codes and frequencies for this variable
        distributions = info.get("value_distributions", [])
        
        if distributions:
            for dist in distributions:
                key_display = str(dist.get("code", ""))
                label = str(dist.get("label", ""))
                freq = dist.get("frequency", 0)
                
                # :<X lines up text to the left; :, adds thousands commas to the numbers
                report_lines.append(f"{key_display:<10} | {label:<35} | {freq:<12,}")
            
            report_lines.append("-" * 65)
            
        # Check for notes inside the keys 'notes', 'notes2', and 'notes3'
        note_keys = ['notes', 'notes2', 'notes3']
        found_notes = []
        for nk in note_keys:
            if nk in info and info[nk]:
                found_notes.append(info[nk])
        
        # If notes were found, write them as a numbered list
        if found_notes:
            report_lines.append("-" * 65)
            report_lines.append("Notes:")
            for index, note_content in enumerate(found_notes, start=1):
                report_lines.append(f"  [{index}] {note_content}")
                
        # Write a closing separator line for the variable block
        report_lines.append("=" * 65 + "\n")
    
    # Join the lines into a single clean string payload
    report_content = "\n".join(report_lines)

    return report_content, (season, year)

def main():
    parser = argparse.ArgumentParser(
        description="Convert a generated Codebook YAML file into a human-readable TXT Codebook report."
    )
    
    # Positional argument for input file
    parser.add_argument(
        "yaml_path",
        help="Path to the target input YAML codebook file (default: %(default)s)"
    )
    
    # Flag argument for managing where the output text file lands
    parser.add_argument(
        "-o", "--output-dir",
        default=".",
        help="Directory where the output TXT report should be saved (default: current directory)"
    )
    
    args = parser.parse_args()
    
    report_payload, metadata = make_codeBook(args.yaml_path)
    season, year = metadata
    
    if season and year:
        output_filename = f"codeBook{season}{year}.txt"
    else:
        output_filename = "codeBook_report.txt"
    
    output_path = os.path.abspath(os.path.join(args.output_dir, output_filename))
    
    # 4. Handle pre-existing file safety sweep cleanly right here
    if os.path.exists(output_path):
        os.remove(output_path)
        
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_payload)

    print(f"Clean frequency report built successfully: {output_path}")


if __name__ == '__main__':
    main()