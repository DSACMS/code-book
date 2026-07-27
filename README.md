# PUF Codebook Generator

A small pipeline for turning Public Use File (PUF) survey data into a structured **YAML codebook** and a human-readable **TXT frequency report**.

It combines:
- A raw survey data file (`.csv`)
- A format catalog (`.txt`) defining value codes and labels
- Excel lookup files for variable formats, variable labels, and variable notes

...into a single YAML codebook describing every variable's format, description, value distributions, related survey questions, and notes. That YAML can then be rendered into a clean text report.

## About the Project

This tool automates the labor-intensive process of documenting survey Public Use Files. Rather than hand-building a codebook for every new year's data release, the pipeline reads the raw survey CSV alongside format/label/notes lookup files and produces a consistent, auditable YAML codebook and companion TXT report — reducing manual transcription errors and making it straightforward to regenerate documentation whenever a new year's data arrives.

## Project Vision

An automated, metadata pipeline where every Medicare Current Beneficiary Survey (MCBS) Public Use File (PUF) release is accompanied by an accurate, reproducible, and machine-readable codebook, eliminating manual documentation drift, reducing reliance on legacy SAS environments, and empowering researchers with open-access data standards.

## Project Mission

Deliver a maintainable and version-controlled Python workflow that ingests raw, open-format CSV survey data and structured, human-editable YAML metadata to generate standardized, machine-readable codebooks and researcher-ready human-readable documentation.

## Agency Mission

This project supports the broader federal initiative of open source software development and transparency in government, aligning with the Federal Source Code Policy (M-16-21) which requires agencies to improve their code sharing practices.

## Team Mission

Our team is committed to building tools that make open source compliance easier for federal development teams, focusing on automation and accuracy to reduce manual overhead.

## Core Team

A list of core team members responsible for the code and documentation in this repository can be found in [COMMUNITY.md](COMMUNITY.md).

## Repository Structure

```
.
├── makeYaml.py                     # Step 1: builds the YAML codebook from source files
├── makeCodebook.py                 # Step 2: converts a YAML codebook into a TXT report
├── makeAll.py                      # Runs both steps end-to-end in one command
├── requirements.txt
├── tests/
│   └── test_makeYaml.py            # Unit tests for makeYaml.py
├── sample1/                        # First sample input set (default arguments paths)
│   ├── sfpuf2023_1_fall.csv        # Source survey data (-f)
│   ├── puf_formats_2023.txt        # Format/value catalog (-c)
│   ├── sfpuf2023_1_fall_formats.xlsx  # Variable format lookup (--format-excel)
│   ├── sfpuf2023_1_fall_labels.xlsx   # Variable label lookup (--label-excel)
│   └── PUFNotes2023.xlsx           # Variable notes lookup (--notes-excel)
└── sample2/                        # Second sample input set
    ├── cspuf2023.csv                  # Source survey data (-f)
    ├── cspuf_formats_2023.txt         # Format/value catalog (-c)
    ├── cspuf2023_formats.xlsx         # Variable format lookup (--format-excel)
    ├── cspuf2023_labels.xlsx          # Variable label lookup (--label-excel)
    └── PUFNotes2023.xlsx              # Variable notes lookup (--notes-excel)
```

## Documentation Index

- [About the Project](#about-the-project)
- [Requirements](#requirements)
- [Expected Input Files](#expected-input-files)
- [Usage](#usage)
- [What Gets Validated](#what-gets-validated)
- [How the Codebook Is Built](#how-the-codebook-is-built)
- [Editing the Metadata Files](#editing-the-metadata-files)
- [Generating Outputs for a New Year](#generating-outputs-for-a-new-year)
- [Known Limitations](#known-limitations)
- [Running Tests](#running-tests)
- [Local Development](#local-development)
- [Coding Style and Linters](#coding-style-and-linters)
- [Development and Software Delivery Lifecycle](#development-and-software-delivery-lifecycle)
- [Branching Model](#branching-model)
- [Contributing](#contributing)
- [Codeowners](#codeowners)
- [Community](#community)
- [Community Guidelines](#community-guidelines)
- [Governance](#governance)
- [Feedback](#feedback)
- [Glossary](#glossary)
- [Policies](#policies)
- [Public Domain](#public-domain)
- [Software Bill of Materials (SBOM)](#software-bill-of-materials-sbom)

## Requirements

```
pandas>=3.0.3
pytest>=9.1.1
PyYAML>=6.0.3
openpyxl>=3.1.5
```

`openpyxl` is required because the Excel lookup files are read via `pandas.read_excel(..., engine="openpyxl")`.

Install with:

```bash
pip install -r requirements.txt
```

## Expected Input Files

```json
{
  "-f, --file": {
    "type": ".csv",
    "description": "Source survey response data. Any filename is accepted as long as it has a .csv extension — there is no required naming pattern. Use -s/--file-name to control the tag baked into the output filename(s)."
  },
  "-c, --catalog": {
    "type": ".txt",
    "description": "PUF format catalog listing 'value <FORMAT_NAME>' blocks with 'code = \"label\"' mappings."
  },
  "--format-excel": {
    "type": ".xlsx / .xls",
    "description": "Maps each Variable to its Format name."
  },
  "--label-excel": {
    "type": ".xlsx / .xls",
    "description": "Maps each Variable to its descriptive Label."
  },
  "--notes-excel": {
    "type": ".xlsx / .xls",
    "description": "Contains per-variable notes (var_nm, qnbr, notes, notes2, notes3), matched on variable name only."
  },
  "-s, --file-name": {
    "type": "string (optional)",
    "description": "Optional tag used to name the output file(s), e.g. 'PUFFALL_2023' produces codebook_PUFFALL_2023.yaml. If omitted, a timestamp (YYYY-MM-DD_HHMMSS) is used instead. Present on makeYaml.py and makeAll.py."
  },
  "-o, --output-dir": {
    "type": "directory",
    "description": "Where the generated file(s) should be saved. Defaults to '.' (the current directory). Present on all three scripts — makeYaml.py, makeCodebook.py, and makeAll.py — and in makeAll.py it controls where both the .yaml and .txt outputs land."
  }
}
```

## Usage

### 1. Generate the YAML codebook only

```bash
python makeYaml.py \
  -f "sample1/sfpuf2023_1_fall.csv" \
  -c "sample1/puf_formats_2023.txt" \
  --format-excel "sample1/sfpuf2023_1_fall_formats.xlsx" \
  --label-excel "sample1/sfpuf2023_1_fall_labels.xlsx" \
  --notes-excel "sample1/PUFNotes2023.xlsx" \
  -s "PUFFALL_2023" \
  -o .
```

Produces `codebook_PUFFALL_2023.yaml` in the output directory. The `-s`/`--file-name` flag is optional — it's just a tag used to name the output file. If you leave it off, the output falls back to a timestamped name (e.g. `codebook_2026-07-27_193000.yaml`), since the tool no longer derives a season/year from the input filename. All other arguments have defaults matching the paths above (all found in the sample1 folder), so running `python makeYaml.py` with no flags will use those defaults (and produce a timestamped output name).

### 2. Generate the TXT report from an existing YAML

```bash
python makeCodebook.py codebook_PUFFALL_2023.yaml
```

Produces `codebook_PUFFALL_2023.txt` in the current directory — the output filename always mirrors the input YAML's basename with a `.txt` extension. Pass `-o` if you want it saved somewhere.

### 3. Run the full pipeline in one step

```bash
python makeAll.py \
  -f "sample1/sfpuf2023_1_fall.csv" \
  -c "sample1/puf_formats_2023.txt" \
  --format-excel "sample1/sfpuf2023_1_fall_formats.xlsx" \
  --label-excel "sample1/sfpuf2023_1_fall_labels.xlsx" \
  --notes-excel "sample1/PUFNotes2023.xlsx" \
  -s "PUFFALL_2023" \
  -o .
```

This runs `makeYaml`'s codebook-building logic and immediately feeds the result into `makeCodebook`'s report generator, producing both the `.yaml` and `.txt` outputs (sharing the same base filename) in one pass.

Like `makeYaml.py`, all of `makeAll.py`'s arguments have defaults matching the paths above, so `python makeAll.py` with no flags at all will also work as long as your files live at those default locations — you'll just get a timestamped output name instead of a tagged one.

## What Gets Validated

- **File extensions**: `check_file_type()` in `makeYaml.py` enforces that each input matches its expected extension (`.csv` for data, `.txt` for the catalog, `.xlsx`/`.xls` for the Excel lookups) and raises a `ValueError` immediately if not.
- **Output naming, not filename parsing**: there's no filename-pattern requirement on the source CSV — `check_file_type()` only checks the extension. The `-s`/`--file-name` flag (present on `makeYaml.py` and `makeAll.py`) is the only thing that controls the tag baked into output filenames; if it's omitted, a timestamp is used instead.
- **Lookup completeness**: `build_codebook_data()` in `makeYaml.py` requires every column in the survey data to have a matching entry in both the format lookup and the label lookup — a missing entry raises a `KeyError`. It also requires each variable's format name to exist in the parsed PUF catalog; if not, a `KeyError` is raised there too.

## How the Codebook Is Built

`build_codebook_data()` in `makeYaml.py` processes each column in the survey data as follows:

1. Look up its **format name** and **description/label**.
2. If that format's catalog block defines a `LOW-HIGH` code — not only when the format is literally named `CONTIN` — collapse all numeric values in the column to that single `LOW-HIGH` placeholder before counting. This makes continuous/ID-style value handling generic to any format that uses a `LOW-HIGH` code, rather than hardcoded to a `CONTIN` format name.
3. Look up value-level labels from the parsed catalog (`parse_catalog`) and count how often each code appears in the data, skipping any codes with zero occurrences.
4. Attach any matching notes and question numbers from the notes Excel file, matched only on variable name (`var_nm`).

The result is dumped to YAML with one entry per variable, e.g.:

```yaml
INT_SPPROXY:
  format: PROXY
  description: Self - respondent or proxy
  value_distributions:
  - code: 1
    label: Self
    frequency: 11437
  - code: 2
    label: Proxy
    frequency: 1579
  qnbr:
  - IN4
  notes: Results include all respondents.
```

`makeCodebook.py` then walks that YAML and renders it as a formatted, fixed-width TXT report with a header, one section per variable, a code/label/frequency table, and any associated question numbers or notes.

## Editing the Metadata Files

If you need to add a variable, change a label, or add a code, edit the underlying source files directly — nothing is meant to be hand-edited in the generated YAML/TXT, since those are regenerated from scratch each run.

Note on multi-sheet workbooks: --format-excel, --label-excel, and --notes-excel are all loaded with pandas.read_excel() without a sheet_name argument, which defaults to reading only the first sheet in the workbook. If any of these files have more than one tab (e.g. one sheet per season, or a leftover "old data" tab), every sheet after the first is silently ignored — there's no warning if the data you actually need is sitting on sheet 2. Keep the data you want processed on the first sheet of each workbook.

### Catalog `.txt` file

Parsed line-by-line by `parse_catalog()`. The expected shape is:

```
value FORMAT_NAME
    1 = "Yes"
    2 = "No"
    . = "Missing";
```

Rules to know when editing:
- A `value <NAME>` line starts a new format block; every `code = "label"` line after it belongs to that format until the next `value` line.
- `FORMAT_NAME` is matched case-insensitively but is stored uppercased, so `value proxy` and `value PROXY` are equivalent.
- Codes can contain letters, numbers, dots, and dashes (e.g. `1`, `.R`, `LOW-HIGH`).
- The label must be in double quotes; a trailing semicolon is optional.
- If a label contains a colon (e.g. `"1: Yes"`), only the text *after* the colon is kept (`"Yes"`). Don't rely on colon-prefixed labels if you want the prefix preserved.
- Lines that don't match the `value` or `code = "label"` patterns exactly are silently ignored — no error is raised, so a typo (missing quote, wrong `=` spacing) just means that code quietly never shows up rather than failing loudly. Double-check new entries render as expected in the output YAML.

### `--format-excel`

Must have at least two columns: `Variable` and `Format`. One row per survey column, mapping it to the format name that should match a `value` block in the catalog (periods are stripped and the value is uppercased before matching, so `contin.` and `Contin` both resolve to `CONTIN`).

### `--label-excel`

Must have at least two columns: `Variable` and `Label`. One row per survey column with its human-readable description.

### `--notes-excel`

Must have at least these columns: `var_nm`, `qnbr`, `notes`, `notes2`, `notes3`. (`file` and `yr` columns may still exist in the sheet for your own record-keeping, but the pipeline no longer reads or filters on them.)
- `var_nm` must match the survey column name exactly — this is now the *only* field used to match a notes row to a variable.
- `qnbr` can hold a comma-separated list (e.g. `"IN4, IN5"`) and becomes a `qnbr` list in the YAML.
- `notes`, `notes2`, `notes3` are free text; empty/NaN cells are skipped, non-empty ones are added verbatim.
- If more than one row matches the same `var_nm` (e.g. leftover rows from a previous year in the same notes file), the last matching row wins and silently overwrites the earlier row's `qnbr`/`notes`/`notes2`/`notes3` values. Keep at most one row per variable in a notes file to avoid issues.
- If your notes workbook has multiple sheets (for example, one tab per year or season), only the first sheet is read — rows on any other sheet are never seen by the pipeline, with no error or warning. Consolidate the notes you need onto the first sheet.


## Generating Outputs for a New Year

There's no year-specific logic hardcoded into the scripts, and the source CSV's filename is no longer parsed for anything — everything is driven purely by the file paths you pass in plus the optional `-s`/`--file-name` tag. To process a new year:

1. **Get the new source CSV**. Any filename works as long as it ends in `.csv` — there's no required naming convention anymore, though keeping a consistent style like `sfpuf<year>_<n>_<season>.csv` (e.g. `sfpuf2024_1_fall.csv`) is still a reasonable convention.
2. **Get or update the catalog `.txt`** for that year. If the value formats haven't changed, you can often reuse last year's catalog — otherwise add/update `value` blocks for any new or changed formats.
3. **Update the format Excel** so every column in the new CSV has a `Variable`/`Format` row.
4. **Update the label Excel** so every column in the new CSV has a `Variable`/`Label` row.
5. **Update the notes Excel** with any new rows for that year/season. Since notes are now matched only on `var_nm`, ensure each variable is only entered into the notes file once to avoid overwritting issues. 
6. **Run `makeAll.py`** pointing at the new year's files, passing `-s` with a tag for the new year so the outputs are named predictably:

For example - 
```bash
python makeAll.py \
  -f "2024Data/sfpuf2024_1_fall.csv" \
  -c "2024Data/puf_formats_2024.txt" \
  --format-excel "2024Data/sfpuf2024_1_fall_formats.xlsx" \
  --label-excel "2024Data/sfpuf2024_1_fall_labels.xlsx" \
  --notes-excel "2024Data/PUFNotes2024.xlsx" \
  -s "PUFFALL_2024" \
  -o .
```

   Leaving off `-s` still works — you'll just get a timestamped filename like `codebook_2026-07-27_193000.yaml` instead of `codebook_PUFFALL_2024.yaml`.
7. Check the console output — any `KeyError` means a survey column is missing from the format or label Excel, or a format name isn't defined in the catalog. Fix the relevant lookup file and re-run.

## Known Limitations

- **No automatic output tagging**: since filenames are no longer parsed for year/season, you have to remember to pass `-s`/`--file-name` yourself if you want a meaningful output name — forgetting it just gives you a timestamped file, which is easy to lose track of across multiple runs.
- **Notes matching ignores file/year**: notes are matched purely on `var_nm`. If a notes Excel file has more than one row for the same variable (e.g. leftover rows from a prior year), only the last matching row's `qnbr`/`notes`/`notes2`/`notes3` survive — there's no season/year disambiguation anymore.
- Only the first sheet of any Excel lookup is read: --format-excel, --label-excel, and --notes-excel are all loaded via pandas.read_excel() with no sheet_name specified, so anything beyond the first sheet in a multi-tab workbook is silently ignored rather than flagged.
- **All-or-nothing lookups**: there's no partial-run or skip-and-warn mode. A single survey column missing from the format Excel, label Excel, or catalog raises a `KeyError` and stops the entire run — you can't generate a partial codebook.
- **Silent catalog parsing failures**: malformed lines in the catalog `.txt` (wrong quoting, unexpected spacing) are skipped without any warning rather than raising an error, so a typo in the catalog can quietly result in a missing code rather than a visible failure.
- **Colon-stripping in labels**: any catalog label containing a colon has everything before the first colon discarded, which may not be what you want for labels that legitimately contain colons. This was done to remove redundant codes placed at the beginning of labels.
- **Overwrites**: existing output files (`.yaml` and `.txt`) are overwritten/removed if they already exist at the target path.
- **Single file per run**: each invocation handles exactly one dataset — there's no built-in batch mode for processing multiple files at once.
- **Test coverage gap**: the test suite (`tests/test_makeYaml.py`) only covers `makeYaml.py`; `makeCodebook.py` and `makeAll.py` currently have no automated tests.

## Running Tests

```bash
pytest tests/
```

The test suite covers:
- `convert()` — numeric string/int/float coercion, including missing-value sentinels (`None`/`NaN` → `"."`) and idempotency on already-typed values
- `check_file_type()` — extension/category validation, including case-insensitivity, whitespace handling, and categories with multiple valid extensions
- `parse_catalog()` — parsing `value`/code-label blocks from the catalog `.txt` file, including colon-stripped labels, mappings that appear before any `value` header (silently ignored), and missing/empty catalog files
- `build_codebook_data()` — full integration of survey data, format/label/notes lookups, and catalog value distributions, including the generalized `LOW-HIGH` bucketing (triggered by the catalog content rather than a hardcoded `CONTIN` format name), missing-lookup `KeyError`s, notes matched purely on `var_nm` (with the last-row-wins behavior explicitly documented), question-number splitting/stripping, and columns with zero overlap against the catalog

## Local Development

1. Clone the repository and `cd` into it.
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # on Windows: .venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Place your source files in the expected locations (see [Repo Structure](#repo-structure)) or pass explicit paths via the CLI flags.
5. Run the pipeline locally with `python makeAll.py` and inspect the generated `.yaml`/`.txt` outputs.
6. Run and or update `pytest tests/` before committing any changes.

## Coding Style and Linters

This project uses **Ruff** for Python code linting and formatting to maintain consistent code quality, clean imports, and standard styling across the codebase.

### Running Linters Locally

Before committing your changes, ensure you have `ruff` installed in your Python environment:

```bash
pip install ruff
```

Then, run the following commands in the root of the repository:

**Check for lint errors and autofix common issues:**

```bash
ruff check . --fix
```

*This checks your code for syntax errors, unused imports, and style violations, automatically fixing what it can.*

**Format your code (rules matching Black):**

```bash
ruff format .
```

*This automatically rewrites your files to match standard Python formatting rules.*

## Development and Software Delivery Lifecycle

This project follows GitHub Actions development practices. For information on contributing, see CONTRIBUTING.md.

## Branching Model

This project follows trunk-based development:

Make small changes in short-lived feature branches and merge to main frequently
Each change merged to main should be immediately deployable
Pull requests are required for all changes
Changes are deployed automatically via GitHub Actions

## Contributing

Thank you for considering contributing to an Open Source project of the US Government! For more information about our contribution guidelines, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Codeowners

The contents of this repository are managed by DSACMS. Those responsible for the code and documentation in this repository can be found in [COMMUNITY.md](COMMUNITY.md). 

## Community

The PUF Codebook Generator team is taking a community-first and open source approach to the product development of this tool. We believe government software should be made in the open and be built and licensed such that anyone can download the code, run it themselves without paying money to third parties or using proprietary software, and use it as they will.

We know that we can learn from a wide variety of communities, including those who will use or will be impacted by the tool, who are experts in technology, or who have experience with similar technologies deployed in other spaces. We are dedicated to creating forums for continuous conversation and feedback to help shape the design and development of the tool.

We also recognize capacity building as a key part of involving a diverse open source community. We are doing our best to use accessible language, provide technical and process documents, and offer support to community members with a wide variety of backgrounds and skillsets.

## Community Guidelines

Principles and guidelines for participating in our open source community can be found in [COMMUNITY.md](COMMUNITY.md). Please read them before joining or starting a conversation in this repo or one of the channels listed below. All community members and participants are expected to adhere to the community guidelines and code of conduct when participating in community spaces including: code repositories, communication channels and venues, and events.

## Governance

This project is governed by our [Community Guidelines](COMMUNITY.md) and [Code of Conduct](CODE_OF_CONDUCT.md). We expect all contributors and maintainers to adhere to these standards to help ensure a welcoming, collaborative, and respectful environment for everyone.

## Feedback

If you have ideas for improvements or encounter any issues, please open an issue on our GitHub repository.

## Glossary

To help new contributors and researchers get up to speed, here are the key domain-specific terms used throughout this repository:

* **PUF (Public Use File):** A de-identified, publicly available dataset released by CMS for researchers and policy analysts to study Medicare demographics, expenditures, and utilization.
* **Codebook:** A comprehensive document that serves as a dictionary for a dataset, describing every variable, its formatting, its source question, and its valid response categories.
* **Metadata:** Structured data that describes other data. In this repository, the metadata acts as the "authoritative source of truth" defining the variables, question mappings, and answer codes that make up our final codebook.
* **Frequency Distribution:** A summary showing the number of times (counts) each discrete value or categorical response occurs in a dataset.
* **SAS (Statistical Analysis System):** A proprietary software suite widely used in government and health policy research for statistical analysis and data management. Historically used to process raw data files and generate codebooks, which this repository's Python-based pipeline is designed to modernize and replace.
* **OEDA (Office of Enterprise Data and Analytics):** The office within CMS responsible for managing enterprise data, generating analytics, and producing files like the MCBS PUF.
* **OSPO (Open Source Program Office):** The entity within CMS that promotes open-source practices, helping project teams build, manage, and release software publicly in a maintainable way.
* **Documentation Drift:** The common issue where database schemas or data files change over time, but the written documentation (such as a PDF codebook) fails to get updated, causing them to fall out of sync.

## Policies

### Open Source Policy

We adhere to the CMS Open Source Policy. If you have any questions, just shoot us an email.

### Security and Responsible Disclosure Policy

For more information about our Security, Vulnerability, and Responsible Disclosure Policies, see SECURITY.md.

## Public Domain

This project is in the public domain within the United States, and copyright and related rights in the work worldwide are waived through the CC0 1.0 Universal public domain dedication as indicated in LICENSE.

All contributions to this project will be released under the CC0 dedication. By submitting a pull request or issue, you are agreeing to comply with this waiver of copyright interest.

## Software Bill of Materials (SBOM)

A Software Bill of Materials (SBOM) is a formal record containing the details and supply chain relationships of various components used in building software.

In the spirit of [Executive Order 14028 - Improving the Nation's Cyber Security](https://www.gsa.gov/technology/it-contract-vehicles-and-purchasing-programs/information-technology-category/it-security/executive-order-14028), a SBOM for this repository is provided here: `https://github.com/DSACMS/code-book/network/dependencies`.

For more information and resources about SBOMs, visit: https://www.cisa.gov/sbom.