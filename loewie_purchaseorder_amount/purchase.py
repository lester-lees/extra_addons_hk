# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import openerp.addons.decimal_precision as dp
import logging
_logger = logging.getLogger(__name__)

class purchase_order(osv.osv):
    _name = "purchase_order"
    _inherit = "purchase.order"

    def _get_order(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('purchase.order.line').browse(cr, uid, ids, context=context):
            result[line.order_id.id] = True
        return result.keys()
		
    def _loewie_amount_all(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
        cur_obj=self.pool.get('res.currency')
		
        zola_pricelist = self.pool.get('product.pricelist').search(cr, uid, [('name','=','Purchase Zalo')], context=context)	
        #_logger.info("Jimmy zola_pricelist :% d" % (len(zola_pricelist) and zola_pricelist[0])	)	
        for order in self.browse(cr, uid, ids, context=context):
            res[order.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_total': 0.0,
            }
            val = val1 = 0.0
            cur_from = order.pricelist_id.currency_id
            cur_to = order.currency_id.id			
            for line in order.order_line:
               val1 += line.price_subtotal
               for c in self.pool.get('account.tax').compute_all(cr, uid, line.taxes_id, line.price_unit, line.product_qty, line.product_id, order.partner_id)['taxes']:
                    val += c.get('amount', 0.0)
					
            #_logger.info("Jimmy cur_to: %d" % cur_to) 
            #_logger.info("Jimmy cur_from: %d" % cur_from.id)			
            if cur_to != cur_from.id and len(zola_pricelist)>0 and order.pricelist_id.id == zola_pricelist[0]: 
                val = cur_obj.compute( cr, uid, cur_from.id, cur_to, val, context=context)	
                val1 = cur_obj.compute( cr, uid, cur_from.id, cur_to, val1, context=context)
                #_logger.info("Jimmy Val :%d" % val)
                #_logger.info("Jimmy Val1 :%d" % val1)				
				
            res[order.id]['amount_tax']=cur_obj.round(cr, uid, cur_from, val)
            res[order.id]['amount_untaxed']=cur_obj.round(cr, uid, cur_from, val1)
            res[order.id]['amount_total']=res[order.id]['amount_untaxed'] + res[order.id]['amount_tax']
        return res
		
    _columns = {		
        'amount_untaxed': fields.function(_loewie_amount_all, digits_compute=dp.get_precision('Account'), string='Untaxed Amount',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The amount without tax", track_visibility='always'),
        'amount_tax': fields.function(_loewie_amount_all, digits_compute=dp.get_precision('Account'), string='Taxes',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The tax amount"),
        'amount_total': fields.function(_loewie_amount_all, digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'purchase.order.line': (_get_order, None, 10),
            }, multi="sums", help="The total amount"),		
    }			