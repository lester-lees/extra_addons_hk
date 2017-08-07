# -*- coding: utf-8 -*-
{
    'name': 'Loewie HK Warehouse Picking list',
    'version': '1.0',
    'author': 'Jimmy.Lee',
    'summary': 'Picking List',
    'description': """
       Jimmy add an oversea_stock_picking
	   'stock_operation_view.xml',	
    """,
    'website': 'http://www.loewie.com',
    'depends': ['stock','sale','report_webkit'],
    'category': 'Printing HK Warehouse Packing',
    'sequence': 116,
    'data': [
        'stock_picking_loewie.xml',
        'stock_operation_view.xml',        	
        'stock_packing_loewie.xml',		
        'stock_layouts_footer.xml',	
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
