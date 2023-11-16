# %%

import layoutparser as lp
import pandas as pd

ocr_agent = lp.TesseractAgent()


# %%


def generate_page_df(pdf_layout, page):

    # try:
    block_dfs = []
    for textblock in range(len(pdf_layout[page])):
        info = {
            "page": page,
            "text_block": textblock,
            "x_start": pdf_layout[page][textblock].block.x_1,
            "x_end": pdf_layout[page][textblock].block.x_2,
            "y_start": pdf_layout[page][textblock].block.y_1,
            "y_end": pdf_layout[page][textblock].block.y_1,
            "text": pdf_layout[page][textblock].text,
            "text_block_id": pdf_layout[page][textblock].id,
            # "text_block_type": pdf_layout[page][textblock].type,
            "text_block_parent": pdf_layout[page][textblock].parent,
            "text_block_next": pdf_layout[page][textblock].next,
            "text_block_score": pdf_layout[page][textblock].score,
        }
        new_df = pd.DataFrame([info], columns=info.keys())
        block_dfs.append(new_df)
    try:
        page_df = pd.concat(block_dfs, axis=0)
    except:
        info = {
            "page": page,
        }
        page_df = pd.DataFrame([info], columns=info.keys())
    return page_df


def generate_pdf_df(file_path, quiet = True):
    if quiet == False:
        print("Extracting from " + document["document_id"])

    try:
        pdf_layouts, pdf_images = lp.load_pdf(file_path, load_images=True)
        page_dfs = []
        for page in range(len(pdf_layouts)):
            new_page_df = generate_page_df(pdf_layouts, page)
            page_dfs.append(new_page_df)
        pdf_df = pd.concat(page_dfs, axis=0)
        pdf_df["ocr"] = 0
        # Add OCR here
        if "text" not in pdf_df.columns:
            if quiet == False:
                print("No text, trying ocr...")
            page_dfs = []
            for page in range(len(pdf_layouts)):
                new_page_df = ocr_agent.detect(pdf_images[page], return_response=True)[
                    "data"
                ]
                new_page_df["page"] = page
                page_dfs.append(new_page_df)
            pdf_df = pd.concat(page_dfs, axis=0)
            pdf_df["ocr"] = 1
            pdf_df = pdf_df.drop("page_num", axis=1)
    except:
        pdf_df = pd.DataFrame.from_dict({"page": [0], "ocr": 0,  "text": [""], "fail": [True]})
    return pdf_df

# %%
