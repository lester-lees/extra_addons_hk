# -*- coding: utf-8 -*-
{
    "name": "Loewie Print out for sales purchase with purchase currency",
    "description": """
Its a sale order report that order line displayed in group and displayed converted currency.

* 150624, Add Taiwan Invioce
* 150526, adapt to purchase order
* 150618, add taiwan invoice
* 151130, add sale custom invoice by jimmy.lee
                    """,
    "version": "0.1",
    "depends": ["base", "sale", "report_webkit","stock","mail"],
    "category": "Reporting",
    "author": "Elico",
    "url": "http://www.elico-corp.com/",
    "data": [
        'product_view.xml',
        'report/sale_report_webkit.xml',
        'report/purchase_report_loewie.xml',
        'report/purchase_report_without_price.xml',
        'report/sale_report_custom.xml',
        'report/sale_report_custom_hk.xml',		
        'security/ir.model.access.csv',
    ],
    "installable": True,
    "auto_install": False,
    "application": True,

}
