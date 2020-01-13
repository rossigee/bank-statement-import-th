from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = 'account.journal'

    statement_parser_class = fields.Char(string='Statement Parser Class')

    def _get_bank_statements_available_import_formats(self):
        """ Adds formats from this module to supported import formats.
        """
        rslt = super(
            AccountJournal,
            self)._get_bank_statements_available_import_formats()
        rslt.append('ktb')
        return rslt
