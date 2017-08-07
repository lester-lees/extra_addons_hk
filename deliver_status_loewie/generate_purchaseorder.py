# -*- coding: utf-8 -*-
from openerp import models, fields, api
import datetime
import logging
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)
		
class generate_purchaseorder(models.TransientModel):
    _name = "generate.purchaseorder"  # purchase
    _description = 'Generate Purchase Order'	

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type Id',required=True)
    company_id = fields.Many2one('res.company', 'Company', required=True)	
    partner_id = fields.Many2one('res.partner','Partner', required=True)
    pricelist_id = fields.Many2one('product.pricelist','Price List', required=True)	
    dest_address_id = fields.Many2one('res.partner', u'发货地址')	
    currency_id = fields.Many2one('res.currency','Currency')	
    location_id = fields.Many2one('stock.location','Supplier Location')	
    #state = fields.Char('State')	
    stock_security_ids = []	
	
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(generate_purchaseorder, self).default_get(cr, uid, fields, context=context)
        self.stock_security_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
		
        if len(self.stock_security_ids)< 1: return res
	
        user_obj = self.pool.get('res.users').browse(cr, uid, [uid], context=context)[0]
		
        pricelist_ids = self.pool.get('product.pricelist').search(cr, uid, [('type', '=', 'purchase')], context=context)
        if len(pricelist_ids)< 1: return res		
        pricelist_obj = self.pool.get('product.pricelist').browse(cr, uid, [pricelist_ids[0]], context=context)
        cid = user_obj.company_id.id or 1	
			
        stock_security_obj = self.pool.get('stock.security').browse(cr, uid, [self.stock_security_ids[0]], context=context)		
        pid = stock_security_obj.supplier_id.id or 1
			
        plid = pricelist_ids[0]		
        ccid = pricelist_obj.currency_id.id		
		
        res.update( picking_type_id = 1, company_id = cid, partner_id=pid, pricelist_id = plid,currency_id=ccid, location_id=8 )

        return res
		

    def generate_purchase_order(self, cr, uid, ids, context=None):		
		
        this = self.pool.get('generate.purchaseorder').browse(cr, uid, [ids[0]], context=context)			
        if len(self.stock_security_ids)< 1: 
            return {'warning': {
            'title': _('Jimmy Warning you'),
            'message': _('You should select at least one product.')
            }}
			
        vals_line = {	
            'product_id': 0,  
            'product_uom_qty':0, 
            'location_dest_id':1, 
            'location_id': 1, 
            'company_id': this.company_id.id, 
            'date':datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'date_expected':(datetime.datetime.now() + datetime.timedelta(3)).strftime("%Y-%m-%d %H:%M:%S"), 
            'invoice_state':'none', 
            'name':'.', 
            'procure_method':'make_to_stock', 
            'state':'draft',			
            'product_uom':1, 
            'weight_uom_id':1,
            'picking_id': 0,			
        }		
		
        vals_purchase = {
            'company_id': this.company_id.id,
            'partner_id': 1, #this.partner_id.id,             			
            'date_order': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),			
            'pricelist_id': this.pricelist_id.id,
            'currency_id': this.currency_id.id,			
            'dest_address_id': this.dest_address_id.id,			
            'picking_type_id': this.dest_address_id and 13 or this.picking_type_id.id,
            'invoice_method': 'order',
            'location_id': this.picking_type_id.default_location_dest_id.id,			
        }

        po_sup_list = {}		
		
        purchase_obj = self.pool.get('purchase.order')
        line_obj = self.pool.get('purchase.order.line')
        stock_security_objs = self.pool.get('stock.security').browse(cr, uid, self.stock_security_ids, context=context).sorted(key=lambda r: r.supplier_id)		
		
        for stock_security_obj in stock_security_objs:
		
            if not stock_security_obj.supplier_id.id in  po_sup_list.keys():
                vals_purchase.update({'partner_id':stock_security_obj.supplier_id.id})	
                vals_purchase['name'] = self.pool.get('ir.sequence').get(cr, uid, 'purchase.order') or '/'				
                purchase_id = purchase_obj.create(cr, uid, vals_purchase, context=context)
                po_sup_list[stock_security_obj.supplier_id.id] = purchase_id		

            qty = stock_security_obj.minimal_qty - stock_security_obj.qty_avail	
            price_unit = line_obj.get_purchase_price(cr, pricelist_id=vals_purchase['pricelist_id'], product_id=stock_security_obj.product_id.id)	
            if qty < 1: continue		
            vals_line.update({'product_id':stock_security_obj.product_id.id, 'product_qty': qty, 'price_unit':price_unit or 0, 'product_uom': stock_security_obj.uom_id.id, 'order_id': po_sup_list[stock_security_obj.supplier_id.id], 'name':'.',  'date_planned': (datetime.datetime.now() + datetime.timedelta(10)).strftime("%Y-%m-%d %H:%M:%S"), 'state':'draft' }) 	
                        		
            line_obj.create(cr, uid, vals_line, context=context)
        url = 'web#page=0&limit=80&view_type=list&model=purchase.order&menu_id=323&action=385'			
        #url = 'web#id=%d&view_type=form&model=purchase.order&menu_id=323&action=385' % purchase_id
        return { 'type' : 'ir.actions.act_url', 'url' : url, 'target' : 'new' }
		