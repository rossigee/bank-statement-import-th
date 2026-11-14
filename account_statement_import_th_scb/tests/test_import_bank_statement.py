import unittest

from odoo.tests.common import TransactionCase, tagged
from odoo.tools import file_path

import base64
import datetime


@tagged('standard', 'at_install')
class TxtFileTest(TransactionCase):
    """Tests for import bank statement Siam Commercial TXT file format
    (account.statement.import)
    """

    def setUp(self):
        super().setUp()
        self.asi_model = self.env['account.statement.import']
        self.as_model = self.env['account.bank.statement']
        self.asl_model = self.env['account.bank.statement.line']

        # Ensure THB currency is active
        cur = self.env['res.currency'].search([
            ('name', '=', 'THB'),
            ('active', '=', False)
        ])
        cur.write({'active': True})

        bank = self.env['res.partner.bank'].create({
            'acc_number': '123456789',
            'partner_id': self.env.ref('base.main_partner').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        # No chart of accounts is installed in the test database, so the
        # journal needs its own bank and suspense accounts.
        bank_account = self.env['account.account'].create({
            'name': 'Test SCB bank',
            'code': 'TSCB01',
            'account_type': 'asset_cash',
        })
        suspense_account = self.env['account.account'].create({
            'name': 'Test SCB suspense',
            'code': 'TSCB02',
            'account_type': 'liability_current',
        })
        journal = self.env['account.journal'].create({
            'name': 'Bank Journal TEST SCB',
            'code': 'BNK12',
            'type': 'bank',
            'bank_account_id': bank.id,
            'currency_id': cur.id,
            'default_account_id': bank_account.id,
            'suspense_account_id': suspense_account.id,
        })
        self.journal_id = journal.id

    def test_wrong_txt_file_import(self):
        txt_file_path = file_path(
            'account_statement_import_th_scb/tests/test_scb_txt_file/test_txt_wrong.txt')
        with open(txt_file_path, 'rb') as f:
            txt_file_wrong = f.read()
        retval = self.asi_model._read_file_scb(data_file=txt_file_wrong)
        self.assertEqual(retval, False)

    def test_txt_file_import(self):
        txt_file_path = file_path(
            'account_statement_import_th_scb/tests/test_scb_txt_file/test_txt.txt')
        with open(txt_file_path, 'rb') as f:
            txt_file = base64.b64encode(f.read())
        wizard = self.asi_model.with_context(journal_id=self.journal_id).create(
            dict(statement_file=txt_file, statement_filename='test_txt.txt'))
        retval = wizard._import_file()
        self.assertEqual(len(retval['notifications']), 0)
        statement_id = retval['statement_ids'][0]

        as_records = self.as_model.search(
            [('id', '=', statement_id)])
        self.assertEqual(len(as_records), 1)
        self.assertTrue(abs(as_records[0].balance_start - 1081.95) < 1)
        self.assertTrue(abs(as_records[0].balance_end_real - 72972.03) < 1)

        asl_records = self.asl_model.search(
            [('payment_ref', 'like', '12342JS001020321')])
        self.assertEqual(len(asl_records), 1)
        self.assertEqual(asl_records[0].date, datetime.date(2020, 1, 2))

    def test_txt_file_th_import(self):
        txt_file_path = file_path(
            'account_statement_import_th_scb/tests/test_scb_txt_file/test_txt_th.txt')
        with open(txt_file_path, 'rb') as f:
            txt_file = base64.b64encode(f.read())
        wizard = self.asi_model.with_context(journal_id=self.journal_id).create(
            dict(statement_file=txt_file, statement_filename='test_txt_th.txt'))
        retval = wizard._import_file()
        self.assertEqual(len(retval['notifications']), 0)
        statement_id = retval['statement_ids'][0]

        as_records = self.as_model.search(
            [('id', '=', statement_id)])
        self.assertEqual(len(as_records), 1)
        # Expected values taken from the two data rows in test_txt_th.txt:
        # first row balance 5335.73 after -50.00, last row balance 5244.57
        # after -91.16.
        self.assertTrue(abs(as_records[0].balance_start - 5385.73) < 0.01)
        self.assertTrue(abs(as_records[0].balance_end_real - 5244.57) < 0.01)

        asl_records = self.asl_model.search(
            [('statement_id', '=', statement_id)], order='date')
        self.assertEqual(len(asl_records), 2)
        self.assertEqual(asl_records[0].date, datetime.date(2020, 4, 5))
        self.assertAlmostEqual(asl_records[0].amount, -50.00)
        self.assertEqual(asl_records[1].date, datetime.date(2020, 4, 7))
        self.assertAlmostEqual(asl_records[1].amount, -91.16)


if __name__ == '__main__':
    unittest.main()
