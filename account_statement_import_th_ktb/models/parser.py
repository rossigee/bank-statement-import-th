"""Class to parse Krungthai bank statement CSV files."""
# Copyright 2023 Ross Golder <ross@golder.org>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

import io
import logging
import hashlib
from lxml import etree

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
        """Parse a Krungthai fake XLS statement file.

        :return: tuple (account_number, statement dict)
        :raises ValueError: if the data is not a KrungThai statement file
        """
        try:
            # Of course, it's not really an XLS file!
            broken_html = "<html>" + data.decode('utf8') + "</html>"
            parser = etree.HTMLParser()
            tree = etree.parse(io.StringIO(broken_html), parser=parser)
        except (ValueError, etree.LxmlError) as e:
            raise ValueError(
                _("The file could not be read as a KrungThai statement: %s", e)
            ) from e

        rows = tree.xpath('/html/body/table/tr')
        if len(rows) < 1:
            raise ValueError(_(
                "No table rows found to parse in statement file. "
                "The file might not be valid."))

        account_number = None
        transactions = []
        first_balance = None
        last_balance = None
        rowcount = 0
        for row in rows:
            values = row.xpath('td')
            rowcount += 1
            if rowcount == 2 and len(values) > 1:
                account_number = values[1].text.lstrip().rstrip().replace('-', ' ')
            if len(values) < 9:
                continue
            dateval = values[0].text.lstrip().rstrip()
            if len(dateval) < 10:
                continue

            # Add this statement line to our results
            vals = self._prepare_transaction_line_ktb(values)
            transactions.append(vals)
            # Running balance column, used to derive the statement balances
            balance = float(values[8].text.lstrip().rstrip().replace(",", ""))
            if first_balance is None:
                first_balance = balance - vals["amount"]
            last_balance = balance

        if not transactions:
            raise ValueError(_("No transactions found in KrungThai statement file."))

        statement = {
            "name": transactions[0]["date"][0:7],
            "date": transactions[-1]["date"],
            "balance_start": first_balance,
            "balance_end_real": last_balance,
            "transactions": transactions,
        }
        return account_number, statement
