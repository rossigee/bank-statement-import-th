"""Class to parse Krungthai bank statement CSV files."""
# Copyright 2023 Ross Golder <ross@golder.org>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import logging
import hashlib
from lxml import etree

from odoo.exceptions import ValidationError

from odoo import api, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

from odoo import _, models

_logger = logging.getLogger(__name__)


class KBizParser(models.AbstractModel):
    """Utility model for parsing KrungThai statements"""

    _name = "account.statement.import.ktb.parser"
    _description = "Account Bank Statement Import KrungThai parser"

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
            #'balance': float(balance)
        }
        return vals
    
    def parse_statement(self, data):
        """Parse a Krungthai fake XLS statement file."""
        try:
            # Of course, it's not really an XLS file!
            broken_html = "<html>" + data.decode('utf8') + "</html>"
            parser = etree.HTMLParser()
            tree = etree.parse(io.StringIO(broken_html), parser=parser)
            rows = tree.xpath('/html/body/table/tr')
            if len(rows) < 1:
                raise ValidationError(_(
                    "No table rows found to parse in statement file. "
                    "The file might not be valid."))
        except Exception as e:
            _logger.error(e)
            return (None, [None])

        statement = {}
        transactions = []
        start_date = None
        end_date = None
        account_number = None

        rowcount = 0
        for row in rows:
            values = row.xpath('td')
            rowcount += 1
            if rowcount == 2:
                account_number = values[1].text.lstrip().rstrip().replace('-', ' ')
            if len(values) < 9:
                continue
            dateval = values[0].text.lstrip().rstrip()
            if len(dateval) < 10:
                continue

            # Add this statement line to our results
            transactions.append(self._prepare_transaction_line_ktb(values))

        # # Look up bank account
        # bank_account = self.env['account.bank.account'].search([
        #     'name', '=', account_number
        # ])
        # _logger.info("Bank account: %s", bank_account)

        statement["name"] = transactions[0]["date"][0:7]
        statement["date"] = transactions[len(transactions) - 1]["date"]
        statement["transactions"] = transactions
            # 'balance_start': balance_start,
            # 'balance_end_real': balance_start + total_amt,

        return statement
    
    def parse(self, data):
        """Parse a KrungThai XLS CSV statement file."""
        statement = self.parse_statement(data)

        # Account number could be included
        return self.env.ref("base.THB").name, None, [statement]
    
    def _parse_file(self, data_file):
        # If we can't read it, pass it to next handler
        (account_number, stmtdata) = self._read_file_ktb(data_file)
        if not stmtdata:
            return super()._parse_file(data_file)

        # Drop 'balance' from raw data, and total up
        transactions = []
        total_amt = 0.00
        lineno = 0
        for vals in stmtdata["transactions"]:
            lineno += 1
            total_amt += float(vals['amount'])
            tx1 = dict(vals)
            #del tx1['balance']
            already_imported = self.env["account.statement.line"].search(
                {[{"unique_import_id", "=", tx1["unique_import_id"]}]}
            )
            if len(already_imported) > 0:
                _logger.warning(_("Statement line %d was already imported", lineno))
                continue
            transactions.append(tx1)
        stmtdata["transactions"] = transactions

        return stmtdata
