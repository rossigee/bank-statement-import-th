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

        cur = self.env['res.currency'].search(
            [('name', 'like', 'THB')], limit=1)
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
        bank_statement.import_file()
        bank_st_record = self.abs_model.search(
            [('name', 'like', 'TR to 7450123086')])[0]
        self.assertEqual(bank_st_record.balance_start, 2516.56)
        self.assertEqual(bank_st_record.balance_end_real, 22223.62)

        line = self.absl_model.search([
            ('name', '=', 'Agrolait'),
            ('statement_id', '=', bank_st_record.id)])[0]
        self.assertEqual(line.ref, '219378')
        self.assertEqual(line.date, datetime.date(2013, 8, 24))
