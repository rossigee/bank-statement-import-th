# Copyright 2023 Ross Golder <ross@golder.org>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import api, models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    @api.model
    def _read_file_ktb(self, data_file):
        """Parse a KrungThai (fake) XLS bank statement file.

        :param data_file: The raw (decoded) file content.
        :return: tuple (account_number, statement dict), or (None, None)
            when the file is not a KrungThai statement, so that the next
            parser in the chain can try it.
        """
        parser = self.env["account.statement.import.ktb.parser"]
        try:
            account_number, statement = parser.parse_statement(data_file)
        except ValueError:
            _logger.debug(
                "File was not recognised as a KrungThai (fake) XLS bank statement file.",
                exc_info=True,
            )
            return (None, None)
        return (account_number, statement)

    def _parse_file(self, data_file):
        account_number, statement = self._read_file_ktb(data_file)
        if statement is None:
            return super()._parse_file(data_file)
        return self.env.ref("base.THB").name, account_number, [statement]
