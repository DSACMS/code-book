import pytest
import pandas as pd
from unittest.mock import mock_open, patch
import sys
from pathlib import Path

file_path = Path(__file__).resolve()
parent_dir = file_path.parent.parent

if str(parent_dir) not in sys.path:
    sys.path.append(str(parent_dir))

from makeYaml import check_file_type, extract_file_metadata, parse_puf_catalog, convert, build_codebook_data

def test_convert_numeric_and_strings():
    """Ensure data types are standardized properly."""
    assert convert("123") == 123
    assert convert("45.6") == 45.6
    assert convert("LOW-HIGH") == "LOW-HIGH"
    
def test_extract_file_metadata_valid():
    """Verify regex correctly parses year and season from standard naming conventions."""
    year, raw_season, fmt_season = extract_file_metadata("Data Files/sfpuf2023_1_fall.csv")
    assert year == 2023
    assert raw_season == "FALL"
    assert fmt_season == "PUF_FALL"
    
def test_extract_file_metadata_invalid():
    """Verify an improperly formatted filename throws an error early."""
    with pytest.raises(ValueError, match="Could not extract year and season from the file name format."):
        extract_file_metadata("wrong_name_format.csv")

def test_check_file_type_validation():
    """Ensure the extension validator guards against incorrect categories."""
    assert check_file_type("data.csv", "data") == "csv"
    assert check_file_type("catalog.txt", "catalog") == "txt"
    assert check_file_type("excel.xlsx", "format-excel") == "xlsx"
    assert check_file_type("label.xls", "label-excel") == "xls"
    assert check_file_type("notes.xlsx", "notes-excel") == "xlsx"
    
    with pytest.raises(ValueError, match="Unsupported file type for data: '.xlsx'. Expected .csv."):
        check_file_type("data.xlsx", "data")
    
    with pytest.raises(ValueError, match="Unknown file category"):
        check_file_type("catalog.txt", "wrong category")
        
def test_parse_puf_caatalog_parsing():
    """Test catalog parsing by mimicking file read operations via mock_open."""
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
        result = parse_puf_catalog("dummy_path.txt")

        assert "YESNOFMT" in result
        assert result["YESNOFMT"]["1"] == "Yes"
        assert result["YESNOFMT"]["2"] == "No"
        assert result["OTHER_FMT"]["."] == "Missing"
        assert result["COMPFMT"][".R"] == "Refused"
        assert result["COMPFMT"]["1"] == "100"

@patch("makeYaml.parse_puf_catalog")
@patch("pandas.read_excel")
@patch("makeYaml.read_data")
def test_build_codebook_data_valid(mock_read_data, mock_read_excel, mock_parse_catalog):
    """Verify build_codebook_data successfully merges survey data, format and 
    label lookup sheets, custom notes, and catalog definitions."""
    mock_survey_df = pd.DataFrame({
        "YESNO": [1, 2, 1, 1, "."],
        "AGE": [".", "R", "LOW-HIGH", "D", "."],
        "PUF_ID": [10001, 10002, 10003, 10004, 10005]
    })
    mock_read_data.return_value = mock_survey_df
    
    mock_format_df = pd.DataFrame([
        {"Variable": "YESNO", "Format": "YESNOFMT"},
        {"Variable": "AGE", "Format": "CONTIN"},
        {"Variable": "PUF_ID", "Format": "PUFFMT"}
    ])
    
    mock_label_df = pd.DataFrame([
        {"Variable": "YESNO", "Label": "Responds either yes or no."},
        {"Variable": "AGE", "Label": "Beneficiary Age"},
        {"Variable": "PUF_ID", "Label": "Beneficiary Identifier"}
    ])
    
    mock_notes_df = pd.DataFrame([
        {
            "var_nm": "YESNO", 
            "file": "PUF_FALL", 
            "yr": 2023, 
            "qnbr": "YN14", 
            "notes": "Test notes",
            "notes2": None,
            "notes3": None
        }
    ])
    
    mock_read_excel.side_effect = [mock_format_df, mock_label_df, mock_notes_df]
    
    mock_parse_catalog.return_value = {
        "YESNOFMT": {"1": "Yes", "2": "No", ".": "Missing"},
        "CONTIN": {"LOW-HIGH": "Range of Values", ".": "Missing", 
                   ".D": "Don't know", ".R": "Refused"},
        "PUFFMT": {"LOW-HIGH": "PUF_ID Count"}
    }
    
    result = build_codebook_data(
        file_path="dummy_survey.csv",
        catalog_path="dummy_catalog.txt",
        format_path="dummy_formats.xlsx",
        label_path="dummy_labels.xlsx",
        notes_path="dummy_notes.xlsx",
        file_year=2023,
        file_season_fmt="PUF_FALL"
    )
    
    assert "YESNO" in result
    assert result["YESNO"]["format"] == "YESNOFMT"
    assert result["YESNO"]["description"] == "Responds either yes or no."
    assert result["YESNO"]["question_numbers"] == ["YN14"]
    assert result["YESNO"]["notes"] == "Test notes"
    
    yesno_dist = result["YESNO"]["value_distributions"]
    assert any(d["code"] == 1 and d["label"] == "Yes" and d["frequency"] == 3 for d in yesno_dist)
    assert any(d["code"] == 2 and d["label"] == "No" and d["frequency"] == 1 for d in yesno_dist)
    assert any(d["code"] == "." and d["label"] == "Missing" and d["frequency"] == 1 for d in yesno_dist)
    
    assert "AGE" in result
    assert result["AGE"]["format"] == "CONTIN"
    assert result["AGE"]["description"] == "Beneficiary Age"
    assert "question_numbers" not in result["AGE"]
    assert "notes" not in result["AGE"]
    
    age_dist = result["AGE"]["value_distributions"]
    assert any(d["code"] == "." and d["label"] == "Missing" and d["frequency"] == 2 for d in age_dist)
    assert any(d["code"] == "R" and d["label"] == "Refused" and d["frequency"] == 1 for d in age_dist)
    assert any(d["code"] == "D" and d["label"] == "Don't know" and d["frequency"] == 1 for d in age_dist)
    assert any(d["code"] == "LOW-HIGH" and d["label"] == "Range of Values" and d["frequency"] == 1 for d in age_dist)
    
    assert "PUF_ID" in result
    assert result["PUF_ID"]["format"] == "PUFFMT"
    assert result["PUF_ID"]["description"] == "Beneficiary Identifier"
    
    puf_id_dist = result["PUF_ID"]["value_distributions"]
    assert puf_id_dist[0]["code"] == "LOW-HIGH"
    assert puf_id_dist[0]["frequency"] == 5