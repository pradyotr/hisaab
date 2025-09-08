# Copyright (c) 2025, Pradyot Raina and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from hisaab.scripts.statement_file_handling import parse_excel_file

class StatementUpload(Document):
	
	def before_insert(self):

		if self.statement_file:
			account_number, ifsc, colmap = parse_excel_file(self.statement_file)
			self.account_number = account_number
			self.ifsc = ifsc
			self.update({
				"date_column": colmap.get("date"),
				"description_column": colmap.get("description"),
				"debit_column": colmap.get("debit"),
				"credit_column": colmap.get("credit"),
				"balance_column": colmap.get("balance")
			})
