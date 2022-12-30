from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
import base64
import datetime


class TestXlsFile(TransactionCase):
    """Tests for import bank statement KrungThai XLS file format
    (account.statement.import)
    """

    def setUp(self):
        super(TestXlsFile, self).setUp()
        self.asi_model = self.env['account.statement.import']
        self.as_model = self.env['account.statement']
        self.j_model = self.env['account.journal']
        self.asl_model = self.env['account.statement.line']

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
        self.journal = self.env['account.journal'].create({
            'name': 'Bank Journal TEST KTB',
            'code': 'BNK12',
            'type': 'bank',
            'bank_account_id': bank.id,
            'currency_id': cur.id,
        })

    def test_wrong_xls_file_import(self):
        xls_file_path = get_module_resource(
            'account_statement_import_th_ktb',
            'tests/test_ktb_xls_file/', 'test_xls_wrong.xls')
        xls_file_wrong = base64.b64encode(open(xls_file_path, 'rb').read())
        bank_statement = self.as_model.create(
            dict(data_file=xls_file_wrong))
        retval = bank_statement._read_file_ktb(data_file=xls_file_wrong)
        self.assertEqual(retval, (None, None))

    def test_xls_file_import(self):
        xls_file_path = get_module_resource(
            'account_statement_import_th_ktb',
            'tests/test_ktb_xls_file/', 'test_xls.xls')
        xls_file = base64.b64encode(open(xls_file_path, 'rb').read())
        bank_statement = self.as_model.create(
            dict(data_file=xls_file))
        retval = bank_statement.import_file()
        self.assertEqual(retval['tag'], "bank_statement_reconciliation_view")
        self.assertEqual(len(retval['context']['notifications']), 0)
        statement_id = retval['context']['statement_ids'][0]

        as_records = self.as_model.search(
            [('id', '=', statement_id)])
        self.assertEqual(len(as_records), 1)
        #self.assertEqual(as_records[0].balance_start, 2516.56)
        self.assertTrue(abs(as_records[0].balance_start - 3904.42) < 1)
        self.assertTrue(abs(as_records[0].balance_end_real - 22223.62) < 1)

        asl_records = self.asl_model.search(
            [('name', 'like', '7450123086')])
        self.assertEqual(len(asl_records), 1)
        self.assertEqual(asl_records[0].date, datetime.date(2020, 1, 4))
