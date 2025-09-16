# Copyright (c) 2025, Pradyot Raina and contributors
# For license information, please see license.txt

# import frappe
from frappe.model.document import Document


class TransactionEntry(Document):
	
	def before_insert(self):
		pass
	
	def after_insert(self):
		if get_float_value(self.debit_amount) > 0:
			self.db_set("amount", self.debit_amount, commit=True, update_modified=False)
			self.db_set("type", "Expense", commit=True, update_modified=False)
			self.db_set("status", "Expense", commit=True, update_modified=False)
		elif get_float_value(self.credit_amount) > 0:
			self.db_set("amount", self.credit_amount, commit=True, update_modified=False)
			self.db_set("type", "Income", commit=True, update_modified=False)
			self.db_set("status", "Income", commit=True, update_modified=False)
	
	def before_save(self):
		self.status = self.type

def get_float_value(value):

	if isinstance(value, str):
		value = value.strip()
		return float(value) if value else 0.0
	
	return float(value)