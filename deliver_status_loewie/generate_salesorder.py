# -*- coding: utf-8 -*-
from openerp import models, fields, api
import datetime
import logging
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)
		
class generate_salesorder(models.TransientModel):
    _name = "generate.salesorder"  # purchase
    _description = 'Generate Purchase Order'	

    company_id = fields.Many2one('res.company', 'Company', required=True)
	
    partner_id = fields.Many2one('res.partner','Partner', required=True)
    partner_invoice_id = fields.Many2one('res.partner','Partner', required=True)
    partner_shipping_id = fields.Many2one('res.partner','Partner', required=True)
	
    warehouse_id = fields.Many2one('stock.warehouse','Warehouse')	
	
    pricelist_id = fields.Many2one('product.pricelist','Price List', required=True)	
	
    product_ids = []	
	
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(generate_salesorder, self).default_get(cr, uid, fields, context=context)
        self.product_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
		
        if len(self.product_ids)< 1: return res
	
        user_obj = self.pool.get('res.users').browse(cr, uid, [uid], context=context)[0]
		
        pricelist_ids = self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'sale')], context=context)
        if len(pricelist_ids)< 1: return res			
		
        res.update( company_id = user_obj.company_id.id or 1, pricelist_id = pricelist_ids[0], warehouse_id=1 )

        return res		

				
    def generate_salesorder(self, cr, uid, ids, context=None ):	
	
        products_obj = self.pool.get('product.product')	
        sale_order_obj = self.pool.get('sale.order')
        sale_order_line_obj = self.pool.get('sale.order.line')		
        this = self.browse(cr, uid, ids[0], context=context)		

        order_vals = {
            'client_order_ref': u'Auto Generated',		
            'picking_policy': 'direct',
            'company_id': this.company_id.id,
            'all_discounts': 0,
            'partner_id': this.partner_id.id,
            'pricelist_id': this.pricelist_id.id or 42, #this.sale_id.pricelist_id.id,
            'warehouse_id': this.warehouse_id.id, #this.picking_type_id.warehouse_id.id,
            'user_id': uid, 
            'state':'draft',
            'partner_invoice_id': this.partner_invoice_id.id or this.partner_id.id, #this.sale_id.partner_invoice_id.id,
            'partner_shipping_id': this.partner_shipping_id.id or this.partner_id.id, #this.sale_id.partner_shipping_id.id,			
            'date_order': datetime.datetime.now(),	
        }
			
        new_id = sale_order_obj.create(cr, uid, order_vals, context=context)
		
        for product in products_obj.browse(cr, uid, self.product_ids, context=context):
            price_unit = sale_order_line_obj.get_price(cr, pricelist_id=order_vals['pricelist_id'], product_id=product.id)		
            order_line = {
                'order_id': new_id,				
                'product_uos_qty': 1,
                'product_id': product.id,
                'product_uom': product.uom_id.id,
                'price_unit': price_unit,
                'product_uom_qty': 1,
                'name': product.description_sale or '.',
                'delay': 7,
                'discount': 0,
            }	

            sale_order_line_obj.create(cr, uid, order_line)			

        sale_order = sale_order_obj.browse(cr, uid, new_id, context=context)
        sale_order_obj.onchange_partner_id(cr, uid, new_id, order_vals['partner_id'], context=context)
        for line in sale_order.order_line:
            line_vals = sale_order_line_obj.product_id_change(
                cr, uid, [line.id], order_vals['pricelist_id'],
                product=line.product_id.id, qty=line.product_uom_qty,
                uom=line.product_uom.id, qty_uos=line.product_uos_qty,
                uos=line.product_uos.id, name=line.name,
                partner_id=order_vals['partner_id'],
                lang=False, update_tax=True, date_order=order_vals['date_order'],
                packaging=False, fiscal_position=False, flag=False, context=context)
            sale_order_line_obj.write(cr, uid, line.id, line_vals['value'], context=context)
			
        return {'type': 'ir.actions.act_url', 'url': "web#id=%s&view_type=form&model=sale.order&action=359" % new_id, 'target': 'new'} 	
	
