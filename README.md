Make sure that you have installed all of the necessary dependencies present in the requirements.txt
There are two scripts makeCodeBook.py and makeYaml.py.

makeYaml.py produces a machine readable YAML file containing all of the necessary information for a codebook. 
To run this program it requires the follow CLI inputs 
1) -f -> this is the data file(sas7bdat)
2) -c -> this is the catalog/format file(sas7bcat)
3) -e -> this is the Excel(xlsx) file containing notes
4) -o -> optional directory location
Example: python3 makeYaml.py -f "Data Files/sfpuf2023_1_fall.sas7bdat" -c "2023 Formats/puf_formats.sas7bcat" -e "2023 PUF Notes/PUFNotes2023.xlsx"

makeCodeBook.py produces a human readable TXT Codebook file, derived from a makeYaml.py YAML output file. 
To run this program use the following CLI inputs
1) a required YAML file location
2) an optional directory location -> -o   
Example: python3 makeCodeBook.py codeBookFALL2023.yaml