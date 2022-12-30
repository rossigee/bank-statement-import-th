"""
Imports one type of KCyber statements
"""

import logging
import io
import csv
import hashlib

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountStatementImportType1(models.TransientModel):
    """
    Imports one type of KCyber statements
    """

    _inherit = 'account.statement.import'

    @api.model
    def _read_file_kcyber_type1(self, data_file):
        _logger.info("Checking upload for match as a KCyber statement (type 1)...")
        try:
            sio = io.StringIO(data_file.decode('utf8'))
            reader = csv.reader(sio)
        except Exception as e:
            _logger.error(e)
            return False

        results = []
        rowcount = 0
        for values in reader:
            rowcount += 1

            # Check 'Date' is on 7th line to confirm this is a KCyber statement
            if rowcount == 7 and values[0] != 'Date':
                _logger.info("Not identified as a KCyber statement (CSV type1)")
                return False

            # Discard header lines
            if rowcount < 8:
                continue

            if len(values) != 8:
                _logger.warning("Wrong number of columns on line (%s)", len(values))
                continue

            # Parse date and amounts
            dateval = values[0]
            if len(dateval) < 10:
                _logger.warning("Wrong number of chars in date (%s)", len(dateval))
                continue
            results.append(self._prepare_transaction_line_kcyber_type1(values))

        if len(results) < 1:
            return False

        return results

    def _prepare_transaction_line_kcyber_type1(self, invals):
        # Parse date, labels and amounts
        dateval = invals[0]
        dateval = f"{dateval[6:10]}-{dateval[3:5]}-{dateval[0:2]}"
        label1 = invals[1]
        label2 = invals[5]
        try:
            debit = 0.0 - float(invals[2].replace(",",""))
        except ValueError:
            debit = 0.0
        try:
            credit = float(invals[3].replace(",",""))
        except ValueError:
            credit = 0.0
        amount = debit + credit
        balance = float(invals[4].replace(",",""))

        hashkey = "".join([invals[0], label1, label2, str(amount), str(balance)])
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
        # Not available in the download
        account_number = None

        # If we can't read it, pass it to next handler
        rawdata = self._read_file_kcyber_type1(data_file)
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
                already_imported = self.env['account.statement.line'].search({
                    [
                        {'unique_import_id', '=', tx['unique_import_id']}
                    ]
                })
                _logger.info(already_imported)
                if len(already_imported) < 1:
                    transactions.append(tx)
        except Exception as e:
            raise UserError(_(
                "The following problem occurred during import. "
                "The file might not be valid.\n\n %s") % e.message)

        vals_bank_statement = {
            'name': account_number,
            'transactions': transactions,
            'balance_start': balance_start,
            'balance_end_real': balance_start + total_amt,
        }
        return "THB", account_number, [
            vals_bank_statement]
