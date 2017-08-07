# -*- coding: utf-8 -*-
{
    'name': 'Loewie MRP',
    'version': '1.0',
    'author': 'Jimmy.Lee',
    'summary': 'Loewie MRP',
    'description': """
      Loewie MRP
    """,
    "depends": [
        "stock",
    ],	
    'website': 'http://www.loewie.com',
    'category': 'Loewie',
    "update_xml": ["mrp_loewie_view.xml","security/security.xml"],	
    'installable': True,
    'application': False,
    'auto_install': False,
}