# Copyright (c) 2025, Pradyot Raina and contributors
# For license information, please see license.txt

from frappe.model.document import Document
from hisaab.scripts.statement_file_handling import parse_excel_file

class StatementUpload(Document):
	
	def before_insert(self):

		if self.statement_file:
			account_number, ifsc = parse_excel_file(self.statement_file)
			self.account_number = account_number
			self.ifsc = ifsc
