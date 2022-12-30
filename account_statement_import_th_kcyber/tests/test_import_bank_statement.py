from odoo.tests.common import TransactionCase
from odoo.modules.module import get_module_resource
from odoo.exceptions import UserError
import base64
import datetime


class TestCsvFile(TransactionCase):
    """Tests for import bank statement Kasikorn KCyber CSV file format
    (account.statement.import)
    """

    def setUp(self):
        super(TestCsvFile, self).setUp()
        self.asi_model = self.env['account.statement.import']
        self.as_model = self.env['account.statement']
        self.asl_model = self.env['account.statement.line']
        self.ia_model = self.env['ir.attachment']

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
            'account_statement_import_th_kcyber',
            'tests/test_kcyber_csv_file/', 'test_csv_wrong.csv')
        csv_file_wrong = base64.b64encode(open(csv_file_path, 'rb').read())
        attachment = self.ia_model.create(
            dict(name="test1",type="binary",datas=csv_file_wrong)
        )
        bank_statement = self.as_model.create(
            dict(attachment_ids=[attachment['id']])
        )
        try:
            retval = bank_statement.import_file()
            self.assertTrue(False) # Should not get to here
        except UserError:
            pass

    def test_csv_file_import_type1(self):
        context = self.env.context.copy()
        context.update({
            'journal_id': self.journal_id
        })
        self.env.context = context

        csv_file_path = get_module_resource(
            'account_statement_import_th_kcyber',
            'tests/test_kcyber_csv_file/', 'test_csv_type1.csv')
        csv_file = base64.b64encode(open(csv_file_path, 'rb').read())
        attachment = self.ia_model.create(
            dict(name="test1",type="binary",datas=csv_file)
        )
        bank_statement = self.as_model.create(
            dict(attachment_ids=[attachment['id']])
        )
        retval = bank_statement.import_file()
        self.assertEqual(retval['tag'], "bank_statement_reconciliation_view")
        self.assertEqual(len(retval['context']['notifications']), 0)
        statement_line_id = retval['context']['statement_line_ids'][0]
        asl_records = self.asl_model.search(
            [('id', '=', statement_line_id)]
        )
        statement = asl_records[0]['statement_id'][0]
        self.assertTrue(abs(statement.balance_start - 15761.6) < 1)
        self.assertTrue(abs(statement.balance_end_real - 14796.6) < 1)

        # asl_records = self.asl_model.search(
        #     [('name', 'like', 'KCB08116')])
        # self.assertEqual(len(asl_records), 1)
        # self.assertEqual(asl_records[0].date, datetime.date(2020, 1, 7))

    def test_csv_file_import_type2(self):
        context = self.env.context.copy()
        context.update({
            'journal_id': self.journal_id
        })
        self.env.context = context

        csv_file_path = get_module_resource(
            'account_statement_import_th_kcyber',
            'tests/test_kcyber_csv_file/', 'test_csv_type2.csv')
        csv_file = base64.b64encode(open(csv_file_path, 'rb').read())
        attachment = self.ia_model.create(
            dict(name="test1",type="binary",datas=csv_file)
        )
        bank_statement = self.as_model.create(
            dict(attachment_ids=[attachment['id']])
        )
        retval = bank_statement.import_file()
        self.assertEqual(retval['tag'], "bank_statement_reconciliation_view")
        self.assertEqual(len(retval['context']['notifications']), 0)
        statement_line_id = retval['context']['statement_line_ids'][0]
        asl_records = self.asl_model.search(
            [('id', '=', statement_line_id)]
        )
        statement = asl_records[0]['statement_id'][0]
        self.assertTrue(abs(statement.balance_start - 17955.99) < 1)
        self.assertTrue(abs(statement.balance_end_real - 19382.62) < 1)

        # asl_records = self.asl_model.search(
        #     [('name', 'like', 'KCB08116')])
        # self.assertEqual(len(asl_records), 1)
        # self.assertEqual(asl_records[0].date, datetime.date(2020, 1, 7))
