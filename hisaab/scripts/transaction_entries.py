import frappe
from frappe.utils import getdate
from hisaab.constants.doctypes import DOCTYPES

def create_transaction_entries(txn_data, colmap, account_number):

    if txn_data.empty or not colmap:
        raise RuntimeError("Data is incomplete or empty.")

    min_date = txn_data.iloc[-1][colmap.get("transaction_date")]
    max_date = txn_data.iloc[0][colmap.get("transaction_date")]

    existing_transactions = frappe.get_list(
        doctype=DOCTYPES.get("Transaction Entry"),
        filters={
            "account": account_number,
            "transaction_date": ["between", [getdate(min_date), getdate(max_date)]]
        },
        fields=["transaction_date", "credit_amount", "debit_amount", "party", "remaining_balance"]
    )

    existing_txn_hash = {
        txn.get("party") for txn in existing_transactions
    }

    # map columns to indices rather than names
    cols = list(txn_data.columns)
    for key, value in colmap.items():
        colmap[key] = cols.index(value)

    for row in txn_data.itertuples(index=False, name=None):
        if row[colmap.get("party")] not in existing_txn_hash:
            data_dict = { col: row[index] for col, index in colmap.items() }
            data_dict["transaction_date"] = getdate(data_dict["transaction_date"])
            data_dict["type"] = "Expense" if (isinstance(data_dict.get("debit_amount"), str) and bool(data_dict.get("debit_amount").strip())) or bool(data_dict.get("debit_amount"))  else "Income"
            doc = frappe.get_doc({
                "doctype": DOCTYPES.get("Transaction Entry"),
                "account": account_number,
                **data_dict
            })
            doc.insert(ignore_permissions=True)
        else:
            break
    
    frappe.db.commit()
