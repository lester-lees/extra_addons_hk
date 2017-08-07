# -*- coding: utf-8 -*-
{
    'name': 'Loewie HK Warehouse Picking transfer details',
    'version': '1.0',
    'author': 'Jimmy.Lee',
    'summary': 'Revise stock transfer details',
    'description': """
       Jimmy add an oversea_stock_picking
	   'stock_operation_view.xml',	
    """,
    'website': 'http://www.loewie.com',
    'depends': ['stock','sale'],
    'category': 'stock.transfer.wizard',
    'data': [
        'stock_transfer_loewie.xml',
        'server_action.xml',		
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}