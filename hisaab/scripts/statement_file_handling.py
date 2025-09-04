import pandas as pd
import spacy
from spacy.matcher import Matcher
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
    
    # find account number
    account_number = find_info_in_text(look_for="Account Number", spacy_doc=doc, nlp=nlp)
    ifsc = find_info_in_text(look_for="IFSC Code", spacy_doc=doc, nlp=nlp)
    
    return account_number, ifsc
