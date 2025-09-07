import frappe
import spacy
import json
import pandas as pd
import numpy as np
from spacy.matcher import Matcher
from datetime import datetime
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

    return pd.notna(arg) and (isinstance(arg, int) or isinstance(arg, float))

def has_atleast_one_letter_and_digit(arg):
    
    return isinstance(arg, str) and (any(char.isalpha() for char in arg) and any(char.isdigit() for char in arg))

def is_valid_locale_date(value):

    try:
        if isinstance(value, datetime):
            return True
        elif isinstance(value, str) and datetime.strptime(value, '%x'):
            return True
    except ValueError:
        return False

def evaluate_combo(df, credit_col, debit_col, balance_col):
    """Return metrics evaluating how well credit/debit explain balance changes."""
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
        mae = float(np.nanmean(np.abs(residuals)))
        medabs = float(np.nanmedian(np.abs(residuals)))

        mean_abs_B = np.nanmean(np.abs(Bx))
        scale = max(1.0, mean_abs_B)
        normalized_rmse = rmse / scale

        # robust linear relation
        slope = np.nan
        intercept = np.nan
        r2 = np.nan
        try:
            # avoid zero-variance
            if np.nanvar(flow_m) > 0:
                slope = float(np.cov(flow_m, dB_m, bias=True)[0,1] / np.nanvar(flow_m))
                intercept = float(np.nanmean(dB_m) - slope * np.nanmean(flow_m))
            r = np.corrcoef(flow_m, dB_m)[0,1]
            r2 = float(r*r)
        except Exception:
            print(Exception.__traceback__)

        score = 1.0 / (1.0 + normalized_rmse) * 100.0
        # bonus if slope ≈ 1 and intercept small and r2 high
        slope_bonus = 0
        if not np.isnan(slope) and abs(slope - 1.0) < 0.1:
            slope_bonus += 10
        if not np.isnan(intercept) and abs(intercept) < 1e-6 * scale + 1.0:
            slope_bonus += 5
        if not np.isnan(r2) and r2 > 0.9:
            slope_bonus += 10

        results.append({
            "orientation": orientation,
            "n_rows": int(n),
            "rmse": rmse,
            "mae": mae,
            "medabs": medabs,
            "normalized_rmse": normalized_rmse,
            "slope": slope,
            "intercept": intercept,
            "r2": r2,
            "score": float(min(100.0, score + slope_bonus))
        })

    # return best result (if any)
    if not results:
        return None
    best = sorted(results, key=lambda x: x["score"], reverse=True)[0]
    return best