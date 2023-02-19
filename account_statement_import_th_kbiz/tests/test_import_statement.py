# Copyright 2023 Ross Golder (https://golder.org)
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).

from odoo import fields
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError

import base64
import json
from datetime import datetime, date

expected = {
    'bad.csv': False,
    'type1.csv': {
        'results': []
    }
}


def compare_txs(a, b):
    ok = True
    attrs = [
        'date',
        'ref',
        'payment_ref',
        'amount',
    ]
    for atx in a:
        foundtx = False
        for btx in b:
            matchcount = 0
            for key in attrs:
                if str(atx[key]) == str(btx[key]):
                    matchcount += 1
            foundtx = matchcount == len(attrs)
            if foundtx:
                break
            ok = False
    return ok


@tagged('golder', 'standard', 'kbiz')
class TestParser(TransactionCase):
    """Tests for the KBiz statement file parser itself."""

    def setUp(self):
        super(TestParser, self).setUp()
        self.parser = self.env["account.statement.import.kbiz.parser"]

    def _do_parse_test(self, inputfile):
        testfile = get_module_resource(
            "account_statement_import_th_kbiz", "tests/test_files", inputfile
        )
        resultfile = get_module_resource(
            "account_statement_import_th_kbiz", "tests/test_files", f"{inputfile}.json"
        )
        with open(testfile, "rb") as data:
            res = self.parser.parse(data.read())
            self.assertTrue(res)
            try:
                with open(resultfile, "r") as result:
                    actual = json.load(result)
                    for i in range(2):
                        self.assertEqual(res[i], actual[i])
            except Exception as e:
                print(f"Result file '{resultfile}' needs to match this...")
                print(json.dumps(res, indent=4))
                self.assertTrue(False)

    def test_parse_type1_th(self):
        self._do_parse_test("type1-th.csv")


@tagged('golder', 'standard', 'kbiz')
class TestImport(TransactionCase):
    """Run test to import KBiz import."""

    def setUp(self):
        super(TestImport, self).setUp()

        # Activate THB currency
        currency = self.env["res.currency"].with_context(active_test=False).search([
            ("name", "=", "THB"),
        ], limit=1).ensure_one()
        currency.action_unarchive()
        currency_id = currency.id

        bank = self.env["res.partner.bank"].create(
            {
                "acc_number": "0123456789",
                "partner_id": self.env.ref("base.main_partner").id,
                "company_id": self.env.ref("base.main_company").id,
                "bank_id": self.env.ref("base.res_bank_1").id,
            }
        )
        self.journal_id = self.env["account.journal"].create(
            {
                "name": "Bank Journal - (test camt)",
                "code": "TBNKCAMT",
                "type": "bank",
                "bank_account_id": bank.id,
                "currency_id": currency_id,
            }
        )

    def test_statement_import(self):
        """Test correct creation of single statement."""
        resultfile = get_module_resource(
            "account_statement_import_th_kbiz", "tests/test_files", "type1-th.csv.json"
        )
        with open(resultfile, "rb") as file:
            testresult = json.load(file)
            txs = testresult[2][0]['transactions']

        testfile = get_module_resource(
            "account_statement_import_th_kbiz", "tests/test_files", "type1-th.csv"
        )
        with open(testfile, "rb") as datafile:
            kbiz_file = base64.b64encode(datafile.read())

            self.env["account.statement.import"].with_context(journal_id=self.journal_id.id).create(
                {
                    "statement_filename": "test import",
                    "statement_file": kbiz_file,
                }
            ).import_file_button()

            bank_st_record = self.env["account.bank.statement"].search(
                [("name", "=", "2023-02")],
                limit=1
            )
            statement_lines = bank_st_record.line_ids

            attrs = [
                'date',
                'ref',
                'payment_ref',
                'amount',
            ]
            for tx in txs:
                foundtx = False
                for line in statement_lines:
                    matchcount = 0
                    for key in attrs:
                        if str(line[key]) == str(tx[key]):
                            matchcount += 1
                    foundtx = matchcount == len(attrs)
                    if foundtx:
                        break
                self.assertTrue(foundtx)