# Copyright 2023 Ross Golder <ross@golder.org>
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

import logging

from odoo import models

_logger = logging.getLogger(__name__)


class AccountBankStatementImport(models.TransientModel):
    _inherit = "account.statement.import"

    def _parse_file(self, data_file):
        """Parse a KrungThai (fake) XLS bank statement file.

        :param data_file: The file to parse.
        :return: The parsed bank statement.
        """

        try:
            parser = self.env["account.statement.import.ktb.parser"]
            _logger.debug("Try parsing with KrungThai parser.")
            return parser.parse(data_file)
        except ValueError:
            _logger.debug(
                "File was not recognised as a KrungThai (fake) XLS bank statement file.", exc_info=True)

        return super()._parse_file(data_file)
