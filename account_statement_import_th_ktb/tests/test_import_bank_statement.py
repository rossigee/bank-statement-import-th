from odoo.tests.common import TransactionCase
from odoo.tools import file_path
import base64
import datetime


class TestXlsFile(TransactionCase):
    """Tests for import bank statement KrungThai XLS file format
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
            'acc_number': '123-0-12345-1',
            'partner_id': self.env.ref('base.main_partner').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        # No chart of accounts is installed in the test database, so the
        # journal needs its own bank and suspense accounts.
        bank_account = self.env['account.account'].create({
            'name': 'Test KTB bank',
            'code': 'TKTB01',
            'account_type': 'asset_cash',
        })
        suspense_account = self.env['account.account'].create({
            'name': 'Test KTB suspense',
            'code': 'TKTB02',
            'account_type': 'liability_current',
        })
        self.journal = self.env['account.journal'].create({
            'name': 'Bank Journal TEST KTB',
            'code': 'BNK12',
            'type': 'bank',
            'bank_account_id': bank.id,
            'currency_id': cur.id,
            'default_account_id': bank_account.id,
            'suspense_account_id': suspense_account.id,
        })

    def test_wrong_xls_file_import(self):
        xls_file_path = file_path(
            'account_statement_import_th_ktb/tests/test_ktb_xls_file/test_xls_wrong.xls')
        with open(xls_file_path, 'rb') as f:
            xls_file_wrong = f.read()
        retval = self.asi_model._read_file_ktb(data_file=xls_file_wrong)
        self.assertEqual(retval, (None, None))

    def test_xls_file_import(self):
        xls_file_path = file_path(
            'account_statement_import_th_ktb/tests/test_ktb_xls_file/test_xls.xls')
        with open(xls_file_path, 'rb') as f:
            xls_file = base64.b64encode(f.read())
        wizard = self.asi_model.create(dict(
            statement_file=xls_file, statement_filename='test_xls.xls'))
        retval = wizard._import_file()
        self.assertEqual(len(retval['notifications']), 0)
        statement_id = retval['statement_ids'][0]

        as_records = self.as_model.search(
            [('id', '=', statement_id)])
        self.assertEqual(len(as_records), 1)
        self.assertTrue(abs(as_records[0].balance_start - 3904.42) < 1)
        self.assertTrue(abs(as_records[0].balance_end_real - 22223.62) < 1)

        asl_records = self.asl_model.search(
            [('payment_ref', 'like', '7450123086')])
        self.assertEqual(len(asl_records), 1)
        self.assertEqual(asl_records[0].date, datetime.date(2020, 1, 4))
