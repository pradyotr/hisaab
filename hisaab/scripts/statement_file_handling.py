import pandas as pd
import spacy
from hisaab.constants.path import BENCH_PATH, SITE_PATH
from hisaab.utils.parsing import find_info_in_text, is_int_or_float, has_atleast_one_letter_and_digit

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

    find_txn_data = find_transaction_data(df)

    if find_txn_data:
        txn_data, metadata = df.iloc[find_txn_data[1]:find_txn_data[2]], pd.concat([df.iloc[:find_txn_data[1]], df.iloc[find_txn_data[2]:]])

    # extract date via pandas
    dates = pd.to_datetime(df.stack(), errors='coerce', format='%x').unstack().dropna(axis=1, how='all').dropna()
    date_columns = dates.columns
    df = df.drop(date_columns, axis=1)

    return account_number, ifsc

def find_transaction_data(df):

    num_counts = df.applymap(is_int_or_float).sum(axis = 1)

    date_mask  = pd.to_datetime(df.stack(), errors='coerce', format='%x').unstack().any(axis = 1)

    alnum_mask = df.applymap(has_atleast_one_letter_and_digit).any(axis = 1)

    reduced_df = df[(num_counts >= 2) & date_mask & alnum_mask]

    transaction_data_candidates = find_transaction_data_candidates(reduced_df)

    if len(transaction_data_candidates) == 1:
        return transaction_data_candidates[0]
    else:
        #handle transaction data edge case confusion
        return False

def find_transaction_data_candidates(df: pd.DataFrame):
    
    index = df.index

    clusters = (index.diff() != 1).cumsum()

    df["cluster"] = clusters

    clustered = df.groupby("cluster")

    cluster_sizes = clustered.size()
    max_cluster_size = cluster_sizes.max()
    max_clusters = cluster_sizes[cluster_sizes == max_cluster_size].index

    candidate_clusters = [
        (len(g.index), min(g.index), max(g.index) + 1) for key, g in df.groupby("cluster") if key in max_clusters
    ]

    return candidate_clusters
        