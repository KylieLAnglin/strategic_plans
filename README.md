# Strategic plans

## File structure
____

```
strategic plans
|
setup.py
|
strategic plans
    |
    --library (contains local modules)
        |_ __init__.py
        |_ start.py (update with local directory locations)
        |_ parse_pdfs.py
    |
    --README.md
    |
    --00_generate_sample (code generating the stratified sample which we collect strategic plans from)
        |_ __init__.py
        |_ ...
    --01_extract_text_for_topic_modeling (code extracting text from pdfs of strategic plans)
        |_ __init__.py
        |_ ...
    --01_import_and_clean_codes (code importing and cleaning human codes from Dedoose)
        |_ __init__.py
        |_ ...
    --02_topic_modeling (code cleaning the text and applying topic models)
        |_ __init__.py
        |_ ...


