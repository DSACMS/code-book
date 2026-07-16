import argparse
import logging
import os
import re

import yaml

logger = logging.getLogger(__name__)


def make_codeBook(yaml_path):
    """
    Reads a variable codebook YAML file and writes a plain text (.txt) report.
    """
    if not os.path.exists(yaml_path):
        raise FileNotFoundError(f"Could not find codebook file at '{yaml_path}'")

    filename = os.path.basename(yaml_path)

    pattern = r"codeBook_([a-zA-Z]+)_(\d+)\.yaml"
    match = re.search(pattern, filename)

    if match:
        season = match.group(1)
        year = match.group(2)
    else:
        season, year = None, None

    with open(yaml_path, encoding="utf-8") as yf:
        codebook = yaml.load(yf, Loader=yaml.SafeLoader)

    if not codebook:
        raise ValueError(
            f"The codebook file at '{yaml_path}' is empty or could not be parsed."
        )

    report_lines = []

    report_lines.append("=" * 70)
    report_lines.append(f"{'PUBLIC USE FILE (PUF) CODEBOOK REPORT':^70}")
    report_lines.append("=" * 70 + "\n")

    for col, info in codebook.items():
        fmt_name = info.get("format", " ")
        var_label = info.get("description", " ")

        report_lines.append(f"Variable Name: {col} (Format: {fmt_name})")
        report_lines.append(f"Description:   {var_label}")
        report_lines.append("-" * 65)
        report_lines.append(f"{'Code':<10} | {'Value Label':<35} | {'Frequency':<12}")
        report_lines.append("-" * 65)

        distributions = info.get("value_distributions", [])

        if distributions:
            for dist in distributions:
                key_display = str(dist.get("code", ""))
                label = str(dist.get("label", ""))
                freq = dist.get("frequency", 0)

                report_lines.append(f"{key_display:<10} | {label:<35} | {freq:<12,}")

            report_lines.append("-" * 65)

        q_numbers = info.get("question_numbers", [])
        if q_numbers:
            q_str = ", ".join(str(q) for q in q_numbers)
            report_lines.append(f"Question(s):   {q_str}")

        note_keys = ["notes", "notes2", "notes3"]
        found_notes = []
        for nk in note_keys:
            if info.get(nk):
                found_notes.append(info[nk])

        if found_notes:
            report_lines.append("-" * 65)
            report_lines.append("Notes:")
            for index, note_content in enumerate(found_notes, start=1):
                report_lines.append(f"  [{index}] {note_content}")

        report_lines.append("=" * 65 + "\n")

    report_content = "\n".join(report_lines)

    return report_content, (season, year)


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    parser = argparse.ArgumentParser(
        description=(
            "Convert a generated Codebook YAML file into "
            "a human-readable TXT Codebook report."
        )
    )

    parser.add_argument(
        "yaml_path",
        help="Path to the target input YAML codebook file (default: %(default)s)",
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

    logger.info(f"Parsing YAML codebook file: {args.yaml_path}")
    report_payload, metadata = make_codeBook(args.yaml_path)
    season, year = metadata

    if season and year:
        output_filename = f"codebook_{season}_{year}.txt"
    else:
        output_filename = "codebook_report.txt"

    output_path = os.path.abspath(os.path.join(args.output_dir, output_filename))

    if os.path.exists(output_path):
        logger.info(f"Overwriting existing file at: {output_path}")
        os.remove(output_path)

    logger.info("Writing text report payload to disk...")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_payload)

    logger.info(f"Clean frequency report built successfully: {output_path}")


if __name__ == "__main__":
    main()
