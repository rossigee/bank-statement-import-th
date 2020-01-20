from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
import base64
import datetime


class TestXlsFile(TransactionCase):
    """Tests for import bank statement KrungThai XLS file format
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestXlsFile, self).setUp()
        self.absi_model = self.env['account.bank.statement.import']
        self.abs_model = self.env['account.bank.statement']
        self.j_model = self.env['account.journal']
        self.absl_model = self.env['account.bank.statement.line']

        # Ensure THB currency is active
        cur = self.env['res.currency'].search([
            ('name', '=', 'THB'),
            ('active', '=', False)
        ])
        cur.write({'active': True})

        bank = self.env['res.partner.bank'].create({
            'acc_number': '123-0-12345-1',
            'partner_id': self.env.ref('base.main_partner').id,
            'company_id': self.env.ref('base.main_company').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        self.env['account.journal'].create({
            'name': 'Bank Journal TEST KTB',
            'code': 'BNK12',
            'type': 'bank',
            'bank_account_id': bank.id,
            'currency_id': cur.id,
        })

    def test_wrong_xls_file_import(self):
        xls_file_path = get_module_resource(
            'account_bank_statement_import_th_ktb',
            'tests/test_ktb_xls_file/', 'test_xls_wrong.xls')
        xls_file_wrong = base64.b64encode(open(xls_file_path, 'rb').read())
        bank_statement = self.absi_model.create(
            dict(data_file=xls_file_wrong))
        self.assertFalse(bank_statement._read_file(data_file=xls_file_wrong))

    def test_xls_file_import(self):
        xls_file_path = get_module_resource(
            'account_bank_statement_import_th_ktb',
            'tests/test_ktb_xls_file/', 'test_xls.xls')
        xls_file = base64.b64encode(open(xls_file_path, 'rb').read())
        bank_statement = self.absi_model.create(
            dict(data_file=xls_file))
        retval = bank_statement.import_file()
        self.assertEqual(retval['tag'], "bank_statement_reconciliation_view")
        self.assertEqual(len(retval['context']['notifications']), 0)
        statement_id = retval['context']['statement_ids'][0]

        abs_records = self.abs_model.search(
            [('id', '=', statement_id)])
        self.assertEqual(len(abs_records), 1)
        #self.assertEqual(abs_records[0].balance_start, 2516.56)
        self.assertTrue(abs(abs_records[0].balance_start - 3904.42) < 1)
        self.assertTrue(abs(abs_records[0].balance_end_real - 22223.62) < 1)

        absl_records = self.absl_model.search(
            [('name', 'like', '7450123086')])
        self.assertEqual(len(absl_records), 1)
        self.assertEqual(absl_records[0].date, datetime.date(2020, 1, 4))
