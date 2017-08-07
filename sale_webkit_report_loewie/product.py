# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import logging

_logger = logging.getLogger(__name__)


class productProduct(osv.osv):
    _inherit = "product.product"
    _columns = {
        'price_hk_sz_exchange':fields.float('Price Between SZ HK'),		
        'purchase_currency_id': fields.many2one('res.currency', 'Currency'),
        'product_type': fields.char('Product Type Label',default='None', help='It used for product report order by.'),
        'product_class': fields.char('Ptoduct Category', translate=True),
        'product_origin': fields.char('Product Original Country',),
        'product_material': fields.char('Product Material'),
        'product_format': fields.char('Product format'),
        'taiwan_invoice': fields.boolean('Taiwan Original Price', default=False,help="if checked ,then report print Original price."),
    }


class res_partner_bank(osv.osv):
    _inherit = "res.partner.bank"
    _columns = {
        'swift_ibna': fields.char('SWIFT/IBNA', size=16),
    }


class product_discount(osv.osv):
    _name = "product.discount"
    _description = "Discount Of Brands For Customer"

    _columns = {
        'country': fields.many2one('res.country','Country'),
        'partner_id': fields.many2one('res.partner', 'Customer'),		
        'brands': fields.char('Brands'),
        'type':fields.selection([('amount','Amount'),('pcs','PCS')],'Type',default='amount'),
        'duration':fields.selection([('monthly','Monthly'),('yearly','Yearly')],'Duration',default='monthly'),		
        'amount': fields.float('Amount'),
        'currency': fields.many2one('res.currency','Currency'),	
        'discount': fields.float('Discount'),
    }

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
