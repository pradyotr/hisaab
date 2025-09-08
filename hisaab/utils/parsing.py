import frappe
import spacy
import json
import pandas as pd
import numpy as np
from spacy.matcher import Matcher
from datetime import datetime
from dateutil.parser import parse
from hisaab.constants.doctypes import DOCTYPES

def find_info_in_text(look_for, text=None, spacy_doc=None, nlp=None):

    valid_types = frappe.get_meta(
        DOCTYPES.get("Pattern Definition"), cached=True
        ).get_field("for").options.split('\n')
    
    if not look_for in valid_types:
        raise RuntimeError(f"ANParser must look for one among {valid_types}")
    
    if not text and not spacy_doc:
        raise RuntimeError("ANParser called without arguements.")

    if not spacy_doc:
        nlp = spacy.load("en_core_web_sm")
        spacy_doc = nlp(text)
    
    matcher = Matcher(nlp.vocab)

    # get match patterns stored in dt
    patterns = frappe.get_list(
        DOCTYPES.get("Pattern Definition"),
        {"for":look_for, "type": "spaCy"},
        pluck="pattern"
    )

    patterns = [ json.loads(pattern) for pattern in patterns ]

    # find account numbers by matching loaded patterns
    matcher.add(look_for, patterns)

    matches = matcher(spacy_doc)

    matches = [ spacy_doc[start:end][-1].text for match_id, start, end in matches ]

    return matches[0] if matches else None

def is_int_or_float(arg):

    return pd.notna(arg) and (isinstance(arg, int) or isinstance(arg, float) or (isinstance(arg, str) and (arg.isdigit() or is_float(arg))))

def has_atleast_one_letter_and_digit(arg):
    
    return isinstance(arg, str) and (any(char.isalpha() for char in arg) and any(char.isdigit() for char in arg))

def is_float(value):

    try:
        if isinstance(value, str) and float(value):
            return True
    except Exception as e:
        return False

def is_valid_locale_date(value):

    try:
        if not pd.notna(value):
            return False
        if isinstance(value, datetime):
            return True
        elif isinstance(value, str) and not value.isdigit() and not is_float(value):
            parse(value, fuzzy=False)
            return True
        else:
            return False
    except ValueError:
        return False

def evaluate_combo(df, credit_col, debit_col, balance_col):
    """Return metrics evaluating how well credit/debit explain balance changes."""
    if not balance_col == 'Unnamed: 6':
        return None
    C = pd.to_numeric(df[credit_col], errors='coerce').values
    C[np.isnan(C)] = 0
    D = pd.to_numeric(df[debit_col], errors='coerce').values
    D[np.isnan(D)] = 0
    B = pd.to_numeric(df[balance_col], errors='coerce').values
    B[np.isnan(B)] = 0
    
    results = []
    for orientation in ("forward", "reverse"):
        if orientation == "reverse":
            Cx, Dx, Bx = C[::-1], D[::-1], B[::-1]
        else:
            Cx, Dx, Bx = C.copy(), D.copy(), B.copy()

        # need at least 2 balances to compute deltas
        if len(Bx) < 2:
            continue

        dB = Bx[1:] - Bx[:-1]
        flow = Cx[1:] - Dx[1:]

        mask = (~np.isnan(dB)) & (~np.isnan(flow))
        dB_m = dB[mask]
        flow_m = flow[mask]

        n = len(dB_m)
        if n < 3:
            continue

        residuals = dB_m - flow_m
        rmse = float(np.sqrt(np.nanmean(residuals**2)))
        
        mean_abs_B = np.nanmean(np.abs(Bx))
        scale = max(1.0, mean_abs_B)
        normalized_rmse = rmse / scale

        score = 1.0 / (1.0 + normalized_rmse) * 100.0

        results.append({
            "orientation": orientation,
            "n_rows": int(n),
            "rmse": rmse,
            "normalized_rmse": normalized_rmse,
            "score": float(min(100.0, score))
        })

    # return best result (if any)
    if not results:
        return None
    
    best = sorted(results, key=lambda x: x["score"], reverse=True)[0]
    return best

def find_spacy_similarity(string, matcher, nlp=None):

    if not nlp:
        nlp = spacy.load("en_core_web_lg")
    
    return nlp(string.lower()).similarity(nlp(matcher.lower()))

def find_best_candidate(candidates, matcher_list, nlp=None):

    if not nlp:
        nlp = spacy.load("en_core_web_lg")
    
    scores = []

    for candidate in candidates:
        score = 0
        for syn in matcher_list:
            sim_score = find_spacy_similarity(candidate, syn, nlp)
            if sim_score == 1:
                return candidate
            score += sim_score
        scores.append(score)
    
    return max(zip(candidates, scores), key=lambda tuple: tuple[1])[0]

def is_date(val: str) -> bool:
    try:
        parse(val, fuzzy=False)
        print(parse(val, fuzzy=False))
        return True
    except Exception:
        return False
