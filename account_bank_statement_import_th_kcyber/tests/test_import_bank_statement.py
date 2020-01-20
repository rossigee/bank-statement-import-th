from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
import base64
import datetime


class TestCsvFile(TransactionCase):
    """Tests for import bank statement Kasikorn KCyber CSV file format
    (account.bank.statement.import)
    """

    def setUp(self):
        super(TestCsvFile, self).setUp()
        self.absi_model = self.env['account.bank.statement.import']
        self.abs_model = self.env['account.bank.statement']
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
        journal = self.env['account.journal'].create({
            'name': 'Bank Journal TEST KCyber',
            'code': 'BNK12',
            'type': 'bank',
            'bank_account_id': bank.id,
            'currency_id': cur.id,
        })
        self.journal_id = journal[0].id

    def test_wrong_csv_file_import(self):
        csv_file_path = get_module_resource(
            'account_bank_statement_import_th_kcyber',
            'tests/test_kcyber_csv_file/', 'test_csv_wrong.csv')
        csv_file_wrong = base64.b64encode(open(csv_file_path, 'rb').read())
        bank_statement = self.absi_model.create(
            dict(data_file=csv_file_wrong))
        retval = bank_statement._read_file_kcyber(data_file=csv_file_wrong)
        self.assertEqual(retval, False)

    def test_csv_file_import(self):
        context = self.env.context.copy()
        context.update({
            'journal_id': self.journal_id
        })
        self.env.context = context

        csv_file_path = get_module_resource(
            'account_bank_statement_import_th_kcyber',
            'tests/test_kcyber_csv_file/', 'test_csv.csv')
        csv_file = base64.b64encode(open(csv_file_path, 'rb').read())
        bank_statement = self.absi_model.create(
            dict(data_file=csv_file))
        retval = bank_statement.import_file()
        self.assertEqual(retval['tag'], "bank_statement_reconciliation_view")
        self.assertEqual(len(retval['context']['notifications']), 0)
        statement_id = retval['context']['statement_ids'][0]

        abs_records = self.abs_model.search(
            [('id', '=', statement_id)])
        self.assertEqual(len(abs_records), 1)
        #self.assertEqual(abs_records[0].balance_start, 2516.56)
        print(abs_records[0].balance_start)
        print(abs_records[0].balance_end_real)
        self.assertTrue(abs(abs_records[0].balance_start - 15761.6) < 1)
        self.assertTrue(abs(abs_records[0].balance_end_real - 14796.6) < 1)

        absl_records = self.absl_model.search(
            [('name', 'like', 'KCB08116')])
        self.assertEqual(len(absl_records), 1)
        self.assertEqual(absl_records[0].date, datetime.date(2020, 1, 7))
