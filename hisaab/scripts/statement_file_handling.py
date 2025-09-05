import pandas as pd
import spacy
from hisaab.constants.path import BENCH_PATH, SITE_PATH
from hisaab.utils.parsing import find_info_in_text

def parse_excel_file(file_path):
    
    full_path = f"{BENCH_PATH}/sites{SITE_PATH[1:]}{file_path}"

    # parse excel for relevant data
    df = pd.read_excel(full_path)
    full_text = df.to_string(index=False, na_rep='')

    # spacy pre processing
    nlp = spacy.load("en_core_web_sm")
    doc = nlp(full_text)
    
    # find bank, account details
    account_number = find_info_in_text(look_for="Account Number", spacy_doc=doc, nlp=nlp)
    ifsc = find_info_in_text(look_for="IFSC Code", spacy_doc=doc, nlp=nlp)

    # parse transactions and reduce dataframe
    df = df.dropna()
    if not df.empty():
        df = df.reset_index(drop=True)
        df.columns = df.iloc[0]
        df = df.iloc[1:]
    else:
        raise RuntimeError("Error while parsing transactions. Index not found.")
    
    # create transaction entries

    # extract date via pandas
    dates = pd.to_datetime(df[:1].stack(), errors='coerce', format='ISO8601').unstack().dropna(axis=1)
    date_columns = dates.columns
    dates = pd.to_datetime(df[date_columns[0]], errors='coerce', format='ISO8601')
    df = df.drop(date_columns, axis=1)

    return account_number, ifsc
