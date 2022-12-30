import unittest

from odoo.tests.common import TransactionCase, tagged
from odoo.modules.module import get_module_resource

import base64
import datetime


@tagged('standard', 'at_install')
class TxtFileTest(TransactionCase):
    """Tests for import bank statement Siam Commercial TXT file format
    (account.statement.import)
    """

    def setUp(self):
        super(TestTxtFile, self).setUp()
        self.as_model = self.env['account.statement.import']
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
            'acc_number': '123456789',
            'partner_id': self.env.ref('base.main_partner').id,
            'company_id': self.env.ref('base.main_company').id,
            'bank_id': self.env.ref('base.res_bank_1').id,
        })
        journal = self.env['account.journal'].create({
            'name': 'Bank Journal TEST SCB',
            'code': 'BNK12',
            'type': 'bank',
            'bank_account_id': bank.id,
            'currency_id': cur.id,
        })
        self.journal_id = journal[0].id

    def test_wrong_txt_file_import(self):
        txt_file_path = get_module_resource(
            'account_statement_import_th_scb',
            'tests/test_scb_txt_file/', 'test_txt_wrong.txt')
        txt_file_wrong = base64.b64encode(open(txt_file_path, 'rb').read())
        bank_statement = self.as_model.create(
            dict(data_file=txt_file_wrong))
        retval = bank_statement._read_file_scb(data_file=txt_file_wrong)
        self.assertEqual(retval, False)

    def test_txt_file_import(self):
        context = self.env.context.copy()
        context.update({
            'journal_id': self.journal_id
        })
        self.env.context = context

        txt_file_path = get_module_resource(
            'account_statement_import_th_scb',
            'tests/test_scb_txt_file/', 'test_txt.txt')
        txt_file = base64.b64encode(open(txt_file_path, 'rb').read())
        bank_statement = self.as_model.create(
            dict(data_file=txt_file))
        retval = bank_statement.import_file()
        self.assertEqual(retval['tag'], "bank_statement_reconciliation_view")
        self.assertEqual(len(retval['context']['notifications']), 0)
        statement_id = retval['context']['statement_ids'][0]

        as_records = self.as_model.search(
            [('id', '=', statement_id)])
        self.assertEqual(len(as_records), 1)
        self.assertTrue(abs(as_records[0].balance_start - 1081.95) < 1)
        self.assertTrue(abs(as_records[0].balance_end_real - 72972.03) < 1)

        asl_records = self.asl_model.search(
            [('name', 'like', '12342JS001020321')])
        self.assertEqual(len(asl_records), 1)
        self.assertEqual(asl_records[0].date, datetime.date(2020, 1, 2))

    def test_txt_file_th_import(self):
        context = self.env.context.copy()
        context.update({
            'journal_id': self.journal_id
        })
        self.env.context = context

        txt_file_path = get_module_resource(
            'account_statement_import_th_scb',
            'tests/test_scb_txt_file/', 'test_txt_th.txt')
        txt_file = base64.b64encode(open(txt_file_path, 'rb').read())
        bank_statement = self.as_model.create(
            dict(data_file=txt_file))
        retval = bank_statement.import_file()
        self.assertEqual(retval['tag'], "bank_statement_reconciliation_view")
        self.assertEqual(len(retval['context']['notifications']), 0)
        statement_id = retval['context']['statement_ids'][0]

        as_records = self.as_model.search(
            [('id', '=', statement_id)])
        self.assertEqual(len(as_records), 1)
        print(as_records[0])
        self.assertTrue(abs(as_records[0].balance_start - 50.00) < 1)
        self.assertTrue(abs(as_records[0].balance_end_real - 72972.03) < 1)

        asl_records = self.asl_model.search(
            [('name', 'like', '12342JS001020321')])
        self.assertEqual(len(asl_records), 1)
        self.assertEqual(asl_records[0].date, datetime.date(2020, 1, 2))


if __name__ == '__main__':
    unittest.main()
