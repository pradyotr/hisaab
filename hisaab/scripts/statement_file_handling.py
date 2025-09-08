import pandas as pd
import spacy
import json
import frappe
from hisaab.constants.path import BENCH_PATH, SITE_PATH
from hisaab.constants.constants import COLMAP
from hisaab.constants.doctypes import DOCTYPES
from hisaab.utils.parsing import find_info_in_text, is_int_or_float, has_atleast_one_letter_and_digit, evaluate_combo, is_valid_locale_date, find_best_candidate

def parse_excel_file(file_path):
    
    full_path = f"{BENCH_PATH}/sites{SITE_PATH[1:]}{file_path}"

    # parse excel for relevant data
    df = pd.read_excel(full_path)
    full_text = df.to_string(index=False, na_rep='')

    # spacy pre processing
    nlp = spacy.load("en_core_web_lg")
    doc = nlp(full_text)
    
    # find bank, account details
    account_number = find_info_in_text(look_for="Account Number", spacy_doc=doc, nlp=nlp)
    ifsc = find_info_in_text(look_for="IFSC Code", spacy_doc=doc, nlp=nlp)

    find_txn_data = find_transaction_data(df)

    if find_txn_data:
        txn_data, metadata = df.iloc[find_txn_data[1]:find_txn_data[2]], pd.concat([df.iloc[:find_txn_data[1]], df.iloc[find_txn_data[2]:]])

        num_cols = []
        date_cols = []
        num_mask = txn_data.applymap(is_int_or_float)
        date_mask  = pd.to_datetime(txn_data.stack(), errors='coerce', format='%x').unstack().applymap(is_valid_locale_date)
        for col in txn_data.columns:
            if num_mask[col].any():
                num_cols.append(col)
            if date_mask[col].all():
                date_cols.append(col)

        amount_columns = find_amount_columns(txn_data, num_cols)

        # find header row
        txn_columns = txn_data.dropna(axis=1, how='all').columns
        txn_header = metadata.dropna(subset=txn_columns)

        # map columns
        if len(txn_header) == 1:
            colmap = COLMAP.copy()
            row = txn_header.iloc[0]
            colmap["debit"]   = row[amount_columns.get("debit_col")]
            colmap["credit"]  = row[amount_columns.get("credit_col")]
            colmap["balance"] = row[amount_columns.get("balance_col")]
            colmap["date"]    = row[date_cols[0]]
            
            # find description column
            description_candidates = [ row[col] for col in txn_data.columns.difference(num_cols + date_cols).tolist()]
            
            synonyms = frappe.get_all(
                DOCTYPES.get("Pattern Definition"),
                {"for": "Header Alias", "type": "spaCy"},
                pluck="pattern"
            )
            if synonyms:
                synonyms = json.loads(synonyms[0])
                colmap["description"] = find_best_candidate(description_candidates, synonyms.get("description"), nlp)
        else:
            # handle multiple hits via spaCy similarity
            pass

        return txn_data, metadata, amount_columns, colmap

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

def find_amount_columns(df, num_cols):

    combos = []

    for credit in num_cols:
        for debit in num_cols:
            if debit == credit: continue
            for balance in num_cols:
                if balance in (credit, debit): continue
                res = evaluate_combo(df, credit, debit, balance)
                if res:
                    res2 = res.copy()
                    res2.update({"credit_col": credit, "debit_col": debit, "balance_col": balance})
                    combos.append(res2)
    if not combos:
        return {}
    return sorted(combos, key=lambda x: x["score"], reverse=True)[0]