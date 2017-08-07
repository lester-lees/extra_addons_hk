# -*- coding: utf-8 -*-
##############################################################################
# For copyright and license notices, see __openerp__.py file in module root
# directory
##############################################################################
from openerp import models, fields, api
import datetime

class sale_order_add_multiple(models.TransientModel):
    _name = 'sale.order.add_multiple'
    _description = 'Sale order add multiple'

    quantity = fields.Float('Quantity', default='1.0')
    products_ids = fields.Many2many( 'product.product', string='Products', domain=[('sale_ok', '=', True)], )

    @api.one
    def add_multiple(self):
        active_id = self._context['active_id']
        sale = self.env['sale.order'].browse(active_id)
        for product_id in self.products_ids:
            product = self.env['sale.order.line'].product_id_change(
                sale.pricelist_id.id,
                product_id.id,
                qty=self.quantity,
                uom=product_id.uom_id.id,
                partner_id=sale.partner_id.id)
            val = {
                'name': product['value'].get('name'),
                'product_uom_qty': self.quantity,
                'order_id': active_id,
                'product_id': product_id.id or False,
                'product_uom': product_id.uom_id.id,
                'price_unit': product['value'].get('price_unit'),
                'tax_id': [(6, 0, product['value'].get('tax_id'))],
            }
            self.env['sale.order.line'].create(val)

class stock_picking_add_multiple(models.TransientModel):
    _name = 'stock.picking.add_multiple'
    _description = 'stock picking add multiple'

    quantity = fields.Float('Quantity', default='1.0')
    products_ids = fields.Many2many( 'product.product', string='Products', domain=[('sale_ok', '=', True)], )	
	
    @api.one
    def add_stock_multiple(self):
        active_id = self._context['active_id']
        picking = self.env['stock.picking'].browse(active_id)
		
        vals = {	
            'picking_id':picking.id,		
            'product_id':0, 
            'product_uom_qty':0, 
            'location_dest_id':picking.picking_type_id.default_location_dest_id.id, 
            'location_id':picking.picking_type_id.default_location_src_id.id, 
            'company_id':picking.company_id.id, 
            'date':datetime.date.today(),
            'date_expected':datetime.date.today() + datetime.timedelta(5), 
            'invoice_state':'none', 
            'name':'.', 
            'procure_method':'make_to_stock', 
            'product_uom':0, 
            'weight_uom_id':0,
        }
		
        for product_id in self.products_ids:

            vals.update( {
                'name': product_id.description_sale or '.',
                'product_uom_qty': self.quantity,
                'product_id': product_id.id or False,
                'product_uom': product_id.uom_id.id,
                'weight_uom_id': product_id.uom_po_id.id,
            } )
            self.env['stock.move'].create(vals)
			

class purchase_order_add_multiple(models.TransientModel):
    _name = 'purchase.order.add_multiple'
    _description = 'purchase order add multiple'

    quantity = fields.Float('Quantity', default='1.0')
    products_ids = fields.Many2many( 'product.product', string='Products', domain=[('sale_ok', '=', True)], )		
	
    @api.one
    def add_purchase_multiple(self):
        active_id = self._context['active_id']
        purchase = self.env['purchase.order'].browse(active_id)
        for product_id in self.products_ids:
            product = self.env['purchase.order.line'].product_id_change(
                purchase.pricelist_id.id,
                product_id.id,
                qty=self.quantity,
                uom_id=product_id.uom_id.id,
                partner_id=purchase.partner_id.id)
            product.update({
                'state': 'draft',
                'date_planned': datetime.date.today() + datetime.timedelta(5),				
                'name': product['value'].get('name'),
                'product_uom_qty': self.quantity,
                'order_id': active_id,
                'product_id': product_id.id or False,
                'product_uom': product_id.uom_id.id,
                'price_unit': product['value'].get('price_unit'),
                'tax_id': [(6, 0, product['value'].get('tax_id'))],
            })
            self.env['purchase.order.line'].create(product)			
