{
    "name": "Terabits Developer Tool",
    "description": """Installing this module, user will able to run python code and sql queries from Odoo.""",
    "version": "17.0.1.1.0",
    'author': 'Terabits Technolab',
    'license': 'AGPL-3',
    'website': 'https://terabits.xyz/',
    "depends": ['base'],
    "data": [
        'views/execute_script_view.xml',
        'security/ir.model.access.csv',
    ],
    "demo_xml": [],
    "images": ["static/description/banner.png"],
    "installable": True,
}
