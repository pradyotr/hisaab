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
    txn_start_index = int(df.dropna().index[0])
    df.columns = df.iloc[txn_start_index]
    df = df.iloc[txn_start_index + 1:]
    df.reset_index(drop=True, inplace=True)

    if df.empty():
        raise RuntimeError("Error while parsing transactions - none found.")
    
    # create transaction entries

    # extract date via pandas
    dates = pd.to_datetime(df.stack(), errors='coerce', format='%x').unstack().dropna(axis=1, how='all').dropna()
    date_columns = dates.columns
    df = df.drop(date_columns, axis=1)

    return account_number, ifsc
