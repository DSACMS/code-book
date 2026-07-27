import argparse
import logging
import os

import yaml

# Initialize module-level logger
logger = logging.getLogger(__name__)


def make_codeBook(yaml_path: str) -> str:
    """
    Reads a variable codebook YAML file and formats its metadata into a
    human-readable, fixed-width text report.

    Parameters
    ----------
    yaml_path : str
        Path to the input YAML codebook file.

    Returns
    -------
    str
        Formatted plain text report ready to be printed or saved to disk.

    Raises
    ------
    FileNotFoundError
        If the provided YAML path does not exist on disk.
    ValueError
        If the YAML file is empty or cannot be parsed into a dictionary.
    """
    # -------------------------------------------------------------------------
    # 1. File Validation & Loading
    # -------------------------------------------------------------------------
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"Could not find codebook file at '{yaml_path}'")

    with open(yaml_path, encoding="utf-8") as yf:
        # Using SafeLoader to avoid executing arbitrary YAML tags
        codebook = yaml.load(yf, Loader=yaml.SafeLoader)

    if not codebook:
        raise ValueError(
            f"The codebook file at '{yaml_path}' is empty or could not be parsed."
        )

    # -------------------------------------------------------------------------
    # 2. Build Report Header
    # -------------------------------------------------------------------------
    report_lines = []

    report_lines.append("=" * 70)
    report_lines.append(f"{'CODEBOOK REPORT':^70}")
    report_lines.append("=" * 70 + "\n")

    # -------------------------------------------------------------------------
    # 3. Process Variables
    # -------------------------------------------------------------------------
    for col, info in codebook.items():
        # Fallback to single spaces if format or description are omitted
        fmt_name = info.get("format", " ")
        var_label = info.get("description", " ")

        report_lines.append(f"Variable Name: {col} (Format: {fmt_name})")
        report_lines.append(f"Description:   {var_label}")
        report_lines.append("-" * 65)
        report_lines.append(f"{'Code':<10} | {'Value Label':<35} | {'Frequency':<12}")
        report_lines.append("-" * 65)

        # Render Value Distributions (Frequencies & Labels)
        distributions = info.get("value_distributions", [])
        if distributions:
            for dist in distributions:
                key_display = str(dist.get("code", ""))
                label = str(dist.get("label", ""))
                freq = dist.get("frequency", 0)

                # Formats frequency with thousands separators (e.g., 1,234)
                report_lines.append(f"{key_display:<10} | {label:<35} | {freq:<12,}")

            report_lines.append("-" * 65)

        # Render Question Numbers
        q_numbers = info.get("qnbr", [])
        if q_numbers:
            q_str = ", ".join(str(q) for q in q_numbers)
            report_lines.append(f"Question(s):   {q_str}")

        # Render Notes
        note_keys = ["notes", "notes2", "notes3"]
        found_notes = [info[nk] for nk in note_keys if info.get(nk)]

        if found_notes:
            report_lines.append("-" * 65)
            report_lines.append("Notes:")
            for index, note_content in enumerate(found_notes, start=1):
                report_lines.append(f"  [{index}] {note_content}")

        # Section separator for the next variable
        report_lines.append("=" * 65 + "\n")

    # Combine all accumulated lines into a single output string
    report_content = "\n".join(report_lines)

    return report_content


def main():
    """CLI entrypoint for converting a YAML codebook into a TXT report."""

    # Configure root logger format for CLI output
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # -------------------------------------------------------------------------
    # CLI Argument Parsing
    # -------------------------------------------------------------------------
    parser = argparse.ArgumentParser(
        description=(
            "Convert a generated Codebook YAML file into "
            "a human-readable TXT Codebook report."
        )
    )

    parser.add_argument(
        "yaml_path",
        help="Path to the target input YAML codebook file.",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        default=".",
        help=(
            "Directory where the output TXT report should "
            "be saved (default: current directory)"
        ),
    )

    args = parser.parse_args()

    # -------------------------------------------------------------------------
    # Execution & File Output
    # -------------------------------------------------------------------------
    logger.info(f"Parsing YAML codebook file: {args.yaml_path}")
    report_payload = make_codeBook(args.yaml_path)

    # Construct destination filename (e.g., 'survey_data.yaml' -> 'survey_data.txt')
    filename = os.path.basename(args.yaml_path)
    filename, _ = os.path.splitext(filename)
    output_filename = f"{filename}.txt"

    output_path = os.path.abspath(os.path.join(args.output_dir, output_filename))

    # Ensure target output directory exists
    os.makedirs(args.output_dir, exist_ok=True)

    # Clean up existing file if present before re-writing
    if os.path.exists(output_path):
        logger.info(f"Overwriting existing file at: {output_path}")
        os.remove(output_path)

    logger.info("Writing text report payload to disk...")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_payload)

    logger.info(f"Clean frequency report built successfully: {output_path}")


if __name__ == "__main__":
    main()
