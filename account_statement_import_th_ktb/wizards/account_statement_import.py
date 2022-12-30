"""
Imports a type of KrungThai statement
"""

import io
import logging
import hashlib
from lxml import etree

from odoo.exceptions import ValidationError

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountStatementImport(models.TransientModel):
    """
    Imports a type of KrungThai statement
    """

    _inherit = 'account.statement.import'

    @api.model
    def _read_file_ktb(self, data_file):
        try:
            # Of course, it's not really an XLS file!
            broken_html = "<html>" + data_file.decode('utf8') + "</html>"
            parser = etree.HTMLParser()
            tree = etree.parse(io.StringIO(broken_html), parser=parser)
            rows = tree.xpath('/html/body/table/tr')
            if len(rows) < 1:
                raise ValidationError(_(
                    "No table rows found to parse in statement file. "
                    "The file might not be valid."))
        except Exception as e:
            _logger.warning(e)
            return (None, None)

        account_number = None
        results = []
        rowcount = 0
        for row in rows:
            values = row.xpath('td')
            rowcount += 1
            if rowcount == 2:
                account_number = values[1].text.lstrip().rstrip()
            if len(values) < 9:
                continue
            dateval = values[0].text.lstrip().rstrip()
            if len(dateval) < 10:
                continue
            results.append(self._prepare_transaction_line_ktb(values))

        return (account_number, results)

    def _prepare_transaction_line_ktb(self, invals):
        # Parse date, labels and amounts
        dateval = invals[0].text.lstrip().rstrip()
        dateval = f"{dateval[6:10]}-{dateval[3:5]}-{dateval[0:2]}"
        label1 = invals[2].text.lstrip().rstrip()
        label2 = invals[3].text.lstrip().rstrip()
        amount = invals[6].text.lstrip().rstrip().replace(",", "")
        balance = invals[8].text.lstrip().rstrip().replace(",", "")

        hashkey = "".join([invals[0].text.lstrip().rstrip(), label1, label2, amount, balance])
        hashval = hashlib.sha256(hashkey.encode('utf-8'))

        vals = {
            'date': dateval,
            'ref': f"{label1}-{label2}",
            'payment_ref': label2,
            'amount': float(amount),
            'unique_import_id': hashval.hexdigest(),
            'balance': float(balance)
        }
        return vals

    def _parse_file(self, data_file):
        # If we can't read it, pass it to next handler
        (account_number, rawdata) = self._read_file_ktb(data_file)
        if not rawdata:
            return super()._parse_file(data_file)

        # Determine start balance for later
        balance_start = rawdata[0]['balance'] - rawdata[0]['amount']

        # Drop 'balance' from raw data, and total up
        transactions = []
        total_amt = 0.00
        try:
            for vals in rawdata:
                total_amt += float(vals['amount'])
                tx = dict(vals)
                del tx['balance']
                transactions.append(tx)
        except Exception as e:
            raise UserError(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s") % e.message)

        vals_bank_statement = {
            'name': transactions[0]['date'][0:7],
            'transactions': transactions,
            'balance_start': balance_start,
            'balance_end_real': balance_start + total_amt,
        }

        return "THB", account_number, [vals_bank_statement]
