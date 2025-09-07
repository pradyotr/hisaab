import frappe
import spacy
import json
import pandas as pd
from spacy.matcher import Matcher
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