"""
Test suite for makeYaml.py
"""

import logging
import re
import sys
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pandas as pd
import pytest

sys.path.append(str(Path(__file__).resolve().parent.parent))

from makeYaml import (
    build_codebook_data,
    check_file_type,
    convert,
    parse_catalog,
)

# ---------------------------------------------------------------------------
# convert()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw, expected",
    [
        # Standard Integer Parsing & Normalization
        ("123", 123),
        ("-7", -7),
        ("007", 7),  # Handles leading zeros
        ("  8  ", 8),  # Strips whitespace automatically
        # Floating Point Parsing (Explicit decimals vs. Scientific notation)
        ("45.6", 45.6),
        ("3.0", 3.0),
        ("1e3", 1000.0),  # Scientific notation triggers the float fallback
        # Missing Data / Sentinel Substitution
        (None, "."),
        (float("nan"), "."),
        # Idempotency (Pre-converted types)
        (123, 123),
        (45.6, 45.6),
        # Non-numeric Fallbacks (Returns original string context)
        ("", ""),
        ("LOW-HIGH", "LOW-HIGH"),
        ("abc", "abc"),
    ],
)
def test_convert_parametrized(raw, expected):
    """
    Verifies that convert() accurately parses numeric strings into native ints/floats,
    normalizes missing/NaN values to '.', and preserves string fallbacks without throwing errors.
    """
    assert convert(raw) == expected


# ---------------------------------------------------------------------------
# check_file_type()
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "path, category, expected_ext",
    [
        # Standard Single-Extension Categories
        ("data.csv", "data", "csv"),
        ("catalog.txt", "catalog", "txt"),
        # Excel Multi-Extension Support (.xlsx vs .xls)
        ("excel.xlsx", "format-excel", "xlsx"),
        ("label.xls", "label-excel", "xls"),
        ("notes.xlsx", "notes-excel", "xlsx"),
        # Case Normalization & Space Sanitization
        ("DATA.CSV", "DATA", "csv"),  # Handles UPPERCASE extensions & categories
        (
            "file.CSV",
            "  data  ",
            "csv",
        ),  # Handles leading/trailing whitespace in category
    ],
)
def test_check_file_type_valid(path, category, expected_ext):
    """Verifies that valid file paths return their clean extension (without leading dot)."""
    assert check_file_type(path, category) == expected_ext


def test_check_file_type_wrong_extension():
    """Ensures an explicit ValueError is raised when an unsupported extension is provided."""
    with pytest.raises(
        ValueError,
        match=re.escape("Unsupported file type for data: '.xlsx'. Expected .csv."),
    ):
        check_file_type("data.xlsx", "data")


def test_check_file_type_no_extension():
    """Verifies that extensionless files (or dotfiles without extensions) trigger file type errors."""
    with pytest.raises(
        ValueError,
        match=re.escape("Unsupported file type for data: ''. Expected .csv."),
    ):
        check_file_type("noext", "data")


def test_check_file_type_unknown_category():
    """Ensures unregistered pipeline categories are rejected immediately."""
    with pytest.raises(ValueError, match="Unknown file category"):
        check_file_type("catalog.txt", "wrong category")


def test_check_file_type_multi_extension_message_lists_both_options():
    """Verifies error messaging for multi-extension rules joins allowed formats with 'or'."""
    with pytest.raises(ValueError, match=r"Expected \.xlsx or \.xls\."):
        check_file_type("thing.csv", "format-excel")


# ---------------------------------------------------------------------------
# parse_catalog()
# ---------------------------------------------------------------------------


def test_parse_catalog_basic_and_semicolon_termination():
    """Verifies parsing of multi-line format blocks, semicolon terminations,
    uppercase format normalization, and colon-prefix stripping in labels."""
    mock_catalog_data = """
    value YESNOFMT
        1 = "Yes"
        2 = "No";
    value OTHER_FMT
        . = "Missing";
    value compfmt
        .R=".R: Refused"
        1 = "100";
    """
    with patch("builtins.open", mock_open(read_data=mock_catalog_data)):
        result = parse_catalog("dummy_path.txt")

    assert result["YESNOFMT"] == {"1": "Yes", "2": "No"}
    assert result["OTHER_FMT"] == {".": "Missing"}

    # Format block names MUST be normalized to UPPERCASE
    assert "COMPFMT" in result and "compfmt" not in result

    # Verify colon prefix removal (e.g., '.R: Refused' -> 'Refused')
    assert result["COMPFMT"][".R"] == "Refused"
    assert result["COMPFMT"]["1"] == "100"


def test_parse_catalog_strips_colon_prefixed_labels():
    """Labels containing a colon (e.g. 'Category: description') should
    keep only the text after the first colon."""
    data = '\nvalue TESTFMT\n1 = "Category A: Description of A"\n'
    with patch("builtins.open", mock_open(read_data=data)):
        result = parse_catalog("x.txt")
    assert result["TESTFMT"]["1"] == "Description of A"


def test_parse_catalog_mapping_before_any_value_block_is_ignored():
    """A key=value line appearing before any 'value X' header has no
    current_value to attach to, and must be silently skipped."""
    data = '\n1 = "Orphaned mapping"\nvalue REALFMT\n2 = "Attached mapping"\n'
    with patch("builtins.open", mock_open(read_data=data)):
        result = parse_catalog("x.txt")
    assert result == {"REALFMT": {"2": "Attached mapping"}}


def test_parse_catalog_missing_file_raises_friendly_error():
    """Missing catalog file should raise FileNotFoundError wrapped with context."""
    with patch("builtins.open", side_effect=FileNotFoundError):
        with pytest.raises(FileNotFoundError, match="Configuration Error"):
            parse_catalog("does_not_exist.txt")


def test_parse_catalog_empty_file_returns_empty_dict():
    """Empty files should yield an empty dictionary without errors."""
    with patch("builtins.open", mock_open(read_data="")):
        assert parse_catalog("empty.txt") == {}


# ---------------------------------------------------------------------------
# Test Helpers
# ---------------------------------------------------------------------------


def _make_excel_side_effect(format_df, label_df, notes_df):
    """Returns a side_effect function so pd.read_excel returns dataframes based
    on file path rather than the order of invocation. Prevents test fragility
    if read order changes.
    """
    mapping = {
        "dummy_formats.xlsx": format_df,
        "dummy_labels.xlsx": label_df,
        "dummy_notes.xlsx": notes_df,
        "fmt.xlsx": format_df,
        "lbl.xlsx": label_df,
        "notes.xlsx": notes_df,
    }

    def _side_effect(path, *args, **kwargs):
        return mapping[path]

    return _side_effect


# ---------------------------------------------------------------------------
# build_codebook_data() - Happy Path
# ---------------------------------------------------------------------------


@patch("makeYaml.parse_catalog")
@patch("pandas.read_excel")
@patch("makeYaml.read_data")
def test_build_codebook_data_valid(
    mock_read_data: MagicMock,
    mock_read_excel: MagicMock,
    mock_parse_catalog: MagicMock,
) -> None:
    """
    Validates end-to-end happy-path execution for build_codebook_data().

    Ensures that categorical frequencies, continuous variable coercion (LOW-HIGH bucketing),
    special missing codes, and metadata (labels, notes, question numbers) are accurately
    aggregated into a structured codebook payload.
    """
    # 1. Arrange: Mock Survey Input Data (using realistic numeric values for AGE)
    # -----------------------------------------------------------------------
    mock_survey_df = pd.DataFrame(
        {
            "YESNO": [1, 2, 1, 1, "."],
            "AGE": [25, 42, "R", "D", "."],  # 2 numbers, 3 special/missing codes
            "PUF_ID": [10001, 10002, 10003, 10004, 10005],
        }
    )
    mock_read_data.return_value = mock_survey_df

    # 2. Arrange: Mock Excel Metadata Tables
    # -----------------------------------------------------------------------
    mock_format_df = pd.DataFrame(
        [
            {"Variable": "YESNO", "Format": "YESNOFMT"},
            {"Variable": "AGE", "Format": "CONTIN"},
            {"Variable": "PUF_ID", "Format": "PUFFMT"},
        ]
    )

    mock_label_df = pd.DataFrame(
        [
            {"Variable": "YESNO", "Label": "Responds either yes or no."},
            {"Variable": "AGE", "Label": "Beneficiary Age"},
            {"Variable": "PUF_ID", "Label": "Beneficiary Identifier"},
        ]
    )

    mock_notes_df = pd.DataFrame(
        [
            {
                "var_nm": "YESNO",
                "file": "PUF_FALL",
                "yr": 2023,
                "qnbr": "YN14",
                "notes": "Test notes",
                "notes2": None,
                "notes3": None,
            }
        ]
    )

    mock_read_excel.side_effect = _make_excel_side_effect(
        mock_format_df, mock_label_df, mock_notes_df
    )

    # 3. Arrange: Mock Parsed Value Catalog
    # -----------------------------------------------------------------------
    mock_parse_catalog.return_value = {
        "YESNOFMT": {"1": "Yes", "2": "No", ".": "Missing"},
        "CONTIN": {
            "LOW-HIGH": "Range of Values",
            ".": "Missing",
            ".D": "Don't know",
            ".R": "Refused",
        },
        "PUFFMT": {"LOW-HIGH": "PUF_ID Count"},
    }

    # 4. Act
    # -----------------------------------------------------------------------
    result = build_codebook_data(
        file_path="dummy_survey.csv",
        catalog_path="dummy_catalog.txt",
        format_path="dummy_formats.xlsx",
        label_path="dummy_labels.xlsx",
        notes_path="dummy_notes.xlsx",
    )

    # 5. Assert: Categorical variable with full metadata and frequency counts
    # -----------------------------------------------------------------------
    assert result["YESNO"]["format"] == "YESNOFMT"
    assert result["YESNO"]["description"] == "Responds either yes or no."
    assert result["YESNO"]["qnbr"] == ["YN14"]
    assert result["YESNO"]["notes"] == "Test notes"

    yesno_dist = {
        (d["code"], d["label"], d["frequency"])
        for d in result["YESNO"]["value_distributions"]
    }
    assert yesno_dist == {
        (1, "Yes", 3),
        (2, "No", 1),
        (".", "Missing", 1),
    }

    # 6. Assert: Continuous variable coerces numbers to LOW-HIGH (freq=2)
    #    while correctly preserving special codes (Refused, Don't know, Missing)
    # -----------------------------------------------------------------------
    assert "qnbr" not in result["AGE"]
    assert "notes" not in result["AGE"]

    age_dist = {
        (d["code"], d["label"], d["frequency"])
        for d in result["AGE"]["value_distributions"]
    }
    assert age_dist == {
        ("LOW-HIGH", "Range of Values", 2),  # 25 and 42 aggregated here
        (".", "Missing", 1),
        ("R", "Refused", 1),
        ("D", "Don't know", 1),
    }

    # 7. Assert: ID Variable (All 5 numeric IDs bucketed into LOW-HIGH)
    # -----------------------------------------------------------------------
    puf_id_dist = result["PUF_ID"]["value_distributions"]
    assert puf_id_dist == [
        {"code": "LOW-HIGH", "label": "PUF_ID Count", "frequency": 5}
    ]


# ---------------------------------------------------------------------------
# build_codebook_data() - Missing Keys
# ---------------------------------------------------------------------------


@patch("makeYaml.parse_catalog")
@patch("pandas.read_excel")
@patch("makeYaml.read_data")
def test_build_codebook_data_column_missing_from_format_key(
    mock_read_data: MagicMock, mock_read_excel: MagicMock, mock_parse_catalog: MagicMock
) -> None:
    """
    Ensures KeyError is raised when a survey column is absent from format_key.
    """
    # Arrange
    mock_read_data.return_value = pd.DataFrame({"UNKNOWN_COL": [1, 2, 3]})
    mock_read_excel.side_effect = _make_excel_side_effect(
        format_df=pd.DataFrame([{"Variable": "SOME_OTHER_COL", "Format": "FMT"}]),
        label_df=pd.DataFrame([{"Variable": "SOME_OTHER_COL", "Label": "label"}]),
        notes_df=pd.DataFrame(
            [
                {
                    "var_nm": "SOME_OTHER_COL",
                    "qnbr": None,
                    "notes": None,
                    "notes2": None,
                    "notes3": None,
                }
            ]
        ),
    )
    mock_parse_catalog.return_value = {"FMT": {"1": "One"}}

    # Act & Assert
    with pytest.raises(KeyError, match=r"UNKNOWN_COL.*not found in format_key"):
        build_codebook_data("f.csv", "c.txt", "fmt.xlsx", "lbl.xlsx", "notes.xlsx")


@patch("makeYaml.parse_catalog")
@patch("pandas.read_excel")
@patch("makeYaml.read_data")
def test_build_codebook_data_column_missing_from_label_key(
    mock_read_data: MagicMock, mock_read_excel: MagicMock, mock_parse_catalog: MagicMock
) -> None:
    """
    Ensures KeyError is raised when a survey column is missing from label_key.
    """
    # Arrange
    mock_read_data.return_value = pd.DataFrame({"FOO": [1, 2, 3]})
    mock_read_excel.side_effect = _make_excel_side_effect(
        format_df=pd.DataFrame([{"Variable": "FOO", "Format": "FMT"}]),
        label_df=pd.DataFrame([{"Variable": "SOME_OTHER_COL", "Label": "label"}]),
        notes_df=pd.DataFrame(
            [
                {
                    "var_nm": "FOO",
                    "qnbr": None,
                    "notes": None,
                    "notes2": None,
                    "notes3": None,
                }
            ]
        ),
    )
    mock_parse_catalog.return_value = {"FMT": {"1": "One"}}

    # Act & Assert
    with pytest.raises(KeyError, match=r"FOO.*not found in label_key"):
        build_codebook_data("f.csv", "c.txt", "fmt.xlsx", "lbl.xlsx", "notes.xlsx")


@patch("makeYaml.parse_catalog")
@patch("pandas.read_excel")
@patch("makeYaml.read_data")
def test_build_codebook_data_format_missing_from_catalog_raises_keyerror(
    mock_read_data: MagicMock, mock_read_excel: MagicMock, mock_parse_catalog: MagicMock
) -> None:
    """
    Verifies that requesting a format not present in the catalog raises a human-readable KeyError.
    """
    # Arrange
    mock_read_data.return_value = pd.DataFrame({"FOO": [1, 2, 3]})
    mock_read_excel.side_effect = _make_excel_side_effect(
        format_df=pd.DataFrame([{"Variable": "FOO", "Format": "MISSINGFMT"}]),
        label_df=pd.DataFrame([{"Variable": "FOO", "Label": "label"}]),
        notes_df=pd.DataFrame(
            [
                {
                    "var_nm": "FOO",
                    "qnbr": None,
                    "notes": None,
                    "notes2": None,
                    "notes3": None,
                }
            ]
        ),
    )
    mock_parse_catalog.return_value = {}  # MISSINGFMT is absent

    # Act & Assert
    with pytest.raises(KeyError, match=r"Format 'MISSINGFMT' not found in the catalog"):
        build_codebook_data("f.csv", "c.txt", "fmt.xlsx", "lbl.xlsx", "notes.xlsx")


# ---------------------------------------------------------------------------
# build_codebook_data() - Logging & Edge Cases
# ---------------------------------------------------------------------------


@patch("makeYaml.parse_catalog")
@patch("pandas.read_excel")
@patch("makeYaml.read_data")
def test_build_codebook_data_no_distributions_logs_debug(
    mock_read_data: MagicMock,
    mock_read_excel: MagicMock,
    mock_parse_catalog: MagicMock,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """
    Verifies that when observed survey values have zero overlap with the catalog,
    value_distributions returns empty and a debug line is logged.
    """
    # Arrange
    mock_read_data.return_value = pd.DataFrame({"FOO": [99, 99]})
    mock_read_excel.side_effect = _make_excel_side_effect(
        format_df=pd.DataFrame([{"Variable": "FOO", "Format": "FMT"}]),
        label_df=pd.DataFrame([{"Variable": "FOO", "Label": "label"}]),
        notes_df=pd.DataFrame(
            [
                {
                    "var_nm": "FOO",
                    "qnbr": None,
                    "notes": None,
                    "notes2": None,
                    "notes3": None,
                }
            ]
        ),
    )
    mock_parse_catalog.return_value = {"FMT": {"1": "One"}}  # No code 99 present

    # Act
    with caplog.at_level(logging.DEBUG, logger="makeYaml"):
        result = build_codebook_data(
            "f.csv", "c.txt", "fmt.xlsx", "lbl.xlsx", "notes.xlsx"
        )

    # Assert
    assert result["FOO"]["value_distributions"] == []
    assert any("value distributions missing" in msg for msg in caplog.messages)


@patch("makeYaml.parse_catalog")
@patch("pandas.read_excel")
@patch("makeYaml.read_data")
def test_build_codebook_data_multiple_notes_rows_last_one_wins(
    mock_read_data: MagicMock, mock_read_excel: MagicMock, mock_parse_catalog: MagicMock
) -> None:
    """
    Current-Behavior Document:

    If multiple rows in notes match the same variable name, the current loop design
    overwrites keys on each iteration. This test documents that last-row-wins behavior.
    """
    # Arrange
    mock_read_data.return_value = pd.DataFrame({"FOO": [1, 1, 1]})
    mock_read_excel.side_effect = _make_excel_side_effect(
        format_df=pd.DataFrame([{"Variable": "FOO", "Format": "FMT"}]),
        label_df=pd.DataFrame([{"Variable": "FOO", "Label": "label"}]),
        notes_df=pd.DataFrame(
            [
                {
                    "var_nm": "FOO",
                    "qnbr": "Q1",
                    "notes": "first note",
                    "notes2": None,
                    "notes3": None,
                },
                {
                    "var_nm": "FOO",
                    "qnbr": "Q2",
                    "notes": "second note",
                    "notes2": None,
                    "notes3": None,
                },
            ]
        ),
    )
    mock_parse_catalog.return_value = {"FMT": {"1": "One"}}

    # Act
    result = build_codebook_data("f.csv", "c.txt", "fmt.xlsx", "lbl.xlsx", "notes.xlsx")

    # Assert: Confirm last row overwritten prior ones
    assert result["FOO"]["qnbr"] == ["Q2"]
    assert result["FOO"]["notes"] == "second note"


@patch("makeYaml.parse_catalog")
@patch("pandas.read_excel")
@patch("makeYaml.read_data")
def test_build_codebook_data_question_numbers_split_and_stripped(
    mock_read_data: MagicMock, mock_read_excel: MagicMock, mock_parse_catalog: MagicMock
) -> None:
    """
    Verifies that question numbers (qnbr) are split on commas, stripped of whitespace,
    and empty elements (like trailing commas) are safely discarded by filtering.
    """
    # Arrange
    mock_read_data.return_value = pd.DataFrame({"FOO": [1, 1]})
    mock_read_excel.side_effect = _make_excel_side_effect(
        format_df=pd.DataFrame([{"Variable": "FOO", "Format": "FMT"}]),
        label_df=pd.DataFrame([{"Variable": "FOO", "Label": "label"}]),
        notes_df=pd.DataFrame(
            [
                {
                    "var_nm": "FOO",
                    "qnbr": " Q1 ,Q2,",
                    "notes": None,
                    "notes2": None,
                    "notes3": None,
                }
            ]
        ),
    )
    mock_parse_catalog.return_value = {"FMT": {"1": "One"}}

    # Act
    result = build_codebook_data("f.csv", "c.txt", "fmt.xlsx", "lbl.xlsx", "notes.xlsx")

    # Assert: Trailing empty string removed by `if q.strip()` list comprehension logic
    assert result["FOO"]["qnbr"] == ["Q1", "Q2"]


@patch("makeYaml.parse_catalog")
@patch("pandas.read_excel")
@patch("makeYaml.read_data")
def test_build_codebook_data_no_matching_notes_rows(
    mock_read_data: MagicMock, mock_read_excel: MagicMock, mock_parse_catalog: MagicMock
) -> None:
    """
    Verifies that variables with no entries in the notes file yield dictionaries
    completely clean of notes-related keys.
    """
    # Arrange
    mock_read_data.return_value = pd.DataFrame({"FOO": [1, 1]})
    mock_read_excel.side_effect = _make_excel_side_effect(
        format_df=pd.DataFrame([{"Variable": "FOO", "Format": "FMT"}]),
        label_df=pd.DataFrame([{"Variable": "FOO", "Label": "label"}]),
        notes_df=pd.DataFrame(
            [
                {
                    "var_nm": "BAR",
                    "qnbr": "Q9",
                    "notes": "irrelevant",
                    "notes2": None,
                    "notes3": None,
                }
            ]
        ),
    )
    mock_parse_catalog.return_value = {"FMT": {"1": "One"}}

    # Act
    result = build_codebook_data("f.csv", "c.txt", "fmt.xlsx", "lbl.xlsx", "notes.xlsx")

    # Assert
    assert "qnbr" not in result["FOO"]
    assert "notes" not in result["FOO"]
