# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)

class purchase_order(osv.osv):
    _inherit = "purchase.order"

    def _undelivered_get(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
		
        for po in self.browse(cr, uid, ids, context=context):
            undeliveryed_pick = ""		
            for pick in po.picking_ids:
                if pick.state in ['assigned','confirmed','partially_available'] : 
                    if undeliveryed_pick != "" : 
                        undeliveryed_pick += "," + pick.name	
                    else: 
                        undeliveryed_pick = pick.name					
            res[po.id] = undeliveryed_pick	

        return res		
		
    _columns = {
        'undelivered': fields.function(_undelivered_get, type="char", copy=False, string='Undelivered', readonly=True, select=True ),		
        #'dest_address_id':fields.many2one('res.partner', u'送货地址',
            states={'confirmed':[('readonly',True)], 'approved':[('readonly',True)],'done':[('readonly',True)]},
            help="Put an address if you want to deliver directly from the supplier to the customer. " \
                "Otherwise, keep empty to deliver to your own company."
        ),
    }
	
    def set_purchase_order_done(self, cr, uid, ids, context=None): 
        if ids : 	
            cr.execute("update purchase_order set state='done' where id=%d" % ids[0])
        return		
	
class product_brand(osv.osv):
    _name = "product.brand"	
	
    _columns = {
        'name' : fields.char('Name', required=True),
        'partner_id': fields.many2one('res.partner','Supplier'),		
    }	
	
class stock_security(osv.osv):
    _name = "stock.security"
    _inherits = {'product.product': 'product_id'}
	
    #def _onhand_qty_get(self, cr, uid, ids, field_name, arg, context=None):	
	
    _columns = {
        #'product_id': fields.many2one('product.product', 'Product', required=True),	
        #'qty_onhand':field.function(_onhand_qty_get, type="integer", copy=False, string='Qty Onhand', readonly=True, select=True ),
		
        'product_id': fields.many2one('product.product', 'Product', required=True, ondelete="cascade", select=True, auto_join=True),	
        'supplier_id': fields.many2one('res.partner','Supplier'),		
        'minimal_qty': fields.integer('Qty Minimal'),		
        'maximal_qty': fields.integer('Qty Maximal'),	
    }
	
	
	