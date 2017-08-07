# -*- coding: utf-8 -*-
from openerp import models, fields, api
import datetime
import logging
from openerp.tools.translate import _
_logger = logging.getLogger(__name__)
		
class warehouse_loewie(models.TransientModel):
    _name = "warehouse.loewie"
    _description = 'Generate Picking wizard'	

    picking_type_id = fields.Many2one('stock.picking.type', 'Picking Type Id',required=True)
    picking_location_id = fields.Many2one('stock.location', string="Source location")
    picking_location_dest_id = fields.Many2one('stock.location', string="Destination location")	
    company_id = fields.Many2one('res.company', 'Company', required=True)	
    partner_id = fields.Many2one('res.partner','Partner', required=True)
    is_include = fields.Boolean('Include ?', default=True)	
    filter_str = fields.Char('Filter String')	
    quants_ids = []	
	
    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(warehouse_loewie, self).default_get(cr, uid, fields, context=context)
        self.quants_ids = context.get('active_ids', [])
        active_model = context.get('active_model')
		
        user_obj = self.pool.get('res.users').browse(cr, uid, [uid], context=context)[0]

        res.update(picking_type_id=3, company_id = user_obj.company_id.id or 1, partner_id = user_obj.partner_id.id or 1 )

        return res
		

    def generate_picking(self, cr, uid, ids, context=None):		
		
        this = self.pool.get('warehouse.loewie').browse(cr, uid, [ids[0]], context=context)			
        if len(self.quants_ids)< 1: 
            return {'warning': {
            'title': _('Jimmy Warning you'),
            'message': _('You should select at least one product.')
            }}
			
        vals_move = {	
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
		
        vals_pick = {
            'company_id': this.company_id.id,
            'partner_id': this.partner_id.id,             			
            'create_date': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),			
            'origin': '.',	
            'move_type': 'direct',
            'picking_type_id': this.picking_type_id.id, 		        			
        }		
		
        pick_obj = self.pool.get('stock.picking')
        move_obj = self.pool.get('stock.move')

        pick_id = pick_obj.create(cr, uid, vals_pick, context=context)
		
        is_include = this.is_include
        filter_str = this.filter_str or ''		
		
        for quant in self.pool.get('stock.quant').browse(cr, uid, self.quants_ids, context=context):
		
            name_template = quant.product_id.name_template
            has_str = name_template.find(filter_str)>=0		# 发现了吗	
            if filter_str and not is_include and has_str : continue	 # 有，不包含，发现了 ---> 跳过
            if filter_str and is_include and not has_str : continue	 # 有，要包含，没发现 ---> 跳过
			
            vals_move.update({'product_id':quant.product_id.id, 'product_uom_qty': quant.qty, 'location_id': quant.location_id.id, 'location_dest_id':  this.picking_location_dest_id.id or this.picking_type_id.default_location_dest_id.id, 'picking_id': pick_id }) 	
                        		
            move_obj.create(cr, uid, vals_move, context=context)			
        url = 'web#id=%d&view_type=form&model=stock.picking&action=162&active_id=%d' % (pick_id, this.picking_type_id.id )
        return { 'type' : 'ir.actions.act_url', 'url' : url, 'target' : 'new' }
		