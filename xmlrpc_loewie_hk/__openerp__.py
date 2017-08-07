# -*- coding: utf-8 -*-
{
    'name': 'Loewie Communication between two Odoo Instances',
    'version': '1.0',
    'author': 'Jimmy.Lee',
    'summary': 'Loewie Communication between two Odoo Instances',
    'description': """
       Loewie Communication between two Odoo Instances	
    """,
    'website': 'http://www.loewie.com',
    'depends': ['base','stock','purchase','sale'],
    'category': 'Loewie',
    "update_xml": ["xmlrpc_loewie.xml",],	
    'installable': True,
    'application': False,
    'auto_install': False,
}