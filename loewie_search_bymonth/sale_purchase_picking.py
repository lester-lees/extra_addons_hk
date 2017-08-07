# -*- encoding: utf-8 -*-
from openerp.osv import fields, osv
from datetime import datetime

class account_invoice(osv.osv):
    _inherit = 'account.invoice'
	
    def _get_confirm_month(self, cr, uid, ids, name, args, context=None):
        res = {}
        for q in self.browse(cr, uid, ids, context=context):
            if not q.picking_id and not q.sale_id : continue
			
            date_confirm = q.picking_id.date_done or q.sale_id.date_confirm	or ''
            if not date_confirm: continue
			
            res[q.id] = (date_confirm[0:7]).replace('-','')
			
        return res
		
    _columns = {
        'confirm_month': fields.function(_get_confirm_month, type='char', string='Inv Month',store=True),		
    }

class sale_order(osv.osv):
    _inherit = 'sale.order'
	
    def _get_confirm_month(self, cr, uid, ids, name, args, context=None):
        res = {}
        for q in self.browse(cr, uid, ids, context=context):
            if not q.date_confirm : 
                continue			
            date_confirm = q.date_confirm	
            res[q.id] = (date_confirm[0:7]).replace('-','')
        return res
		
    _columns = {
        'confirm_month': fields.function(_get_confirm_month, type='char', string='Confirm Month',store=True),		
    }
	
class purchase_order(osv.osv):
    _inherit = 'purchase.order'
	
    def _get_confirm_month(self, cr, uid, ids, name, args, context=None):
        res = {}
        for q in self.browse(cr, uid, ids, context=context):
            if not q.date_approve : 
                continue			
            date_confirm = str(q.date_approve)	
            res[q.id] = (date_confirm[0:7]).replace('-','')
        return res
		
    _columns = {
        'confirm_month': fields.function(_get_confirm_month, type='char', string='Approve Month',store=True),		
    }	
	
class stock_picking(osv.osv):
    _inherit = 'stock.picking'
	
    def _get_confirm_month(self, cr, uid, ids, name, args, context=None):
        res = {}
        for q in self.browse(cr, uid, ids, context=context):
            if not q.date_done : 
                continue			
            date_confirm = str(q.date_done)	
            res[q.id] = (date_confirm[0:7]).replace('-','')
        return res
		
    _columns = {
        'confirm_month': fields.function(_get_confirm_month, type='char', string='Transfer Month',store=True),		
    }		