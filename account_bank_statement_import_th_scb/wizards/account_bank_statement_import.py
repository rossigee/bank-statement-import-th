import logging
import io
import hashlib
from lxml import etree

from odoo.exceptions import ValidationError

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = 'account.bank.statement.import'

    @api.model
    def _read_file(self, data_file):
        try:
            sio = io.StringIO(data_file.decode('utf8'))
            lines = sio.readlines()
        except Exception as e:
            print(e)
            _logger.debug(e)
            return False

        results = []
        for line in lines:
            values = line.rstrip().split('\t')
            if(len(values) < 9):
                continue
            dateval = values[0]
            if(len(dateval) < 10):
                continue
            results.append(self._prepare_transaction_line(values))
        return results

    def _prepare_transaction_line(self, invals):
        # Parse date, labels and amounts
        dateval = invals[0]
        dateval = "{}-{}-{}".format(dateval[6:10], dateval[3:5], dateval[0:2])
        label1 = invals[3]
        label2 = invals[4]
        try:
            debit = float(invals[6].replace(",",""))
        except ValueError:
            debit = 0.0
        try:
            credit = float(invals[7].replace(",",""))
        except ValueError:
            credit = 0.0
        amount = debit + credit
        balance = float(invals[8].replace(",",""))

        hashkey = "".join([dateval, label1, label2, str(amount), str(balance)])
        hash = hashlib.sha256(hashkey.encode('utf-8'))

        vals = {
            'date': dateval,
            'name': label2,
            #'ref': label2,
            'amount': float(amount),
            'unique_import_id': hash.hexdigest(),
            'balance': float(balance)
        }
        return vals

    def _parse_file(self, data_file):
        # Not available in the download
        account_number = None

        # If we can't read it, pass it to next handler
        rawdata = self._read_file(data_file)
        if not rawdata:
            return super(AccountBankStatementImport, self)._parse_file(data_file)

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
            print(e)
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
