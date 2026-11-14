{
    'name': 'Import Siam Commercial Bank Statement',
    'category': 'Banking addons',
    'version': '18.0.1.1.0',
    'license': 'AGPL-3',
    'author': 'Ross Golder',
    'website': "https://www.golder.org",
    'depends': [
        'account_statement_import_file',
    ],
    'data': [
        'views/account_statement_import.xml',
    ],
    'installable': True,
}
