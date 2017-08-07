# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import logging

_logger = logging.getLogger(__name__)

class stock_move(osv.osv):
    _inherit = "stock.move"
    _order = 'id , date_expected desc'
	
    def _get_sale_order_line(self, cr, uid, ids, field_name, arg, context=None):	
        result = {}
        for move in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            result[move.id] = move.procurement_id.sale_line_id.id
        return result	
	
    _columns = {
        'sale_order_line': fields.function(_get_sale_order_line, type='many2one', relation='sale.order.line',string='Sales Line'),		
    }
	
	
class stock_picking(osv.osv):
    _inherit = 'stock.picking'
    _order = "id desc, priority desc, date asc"
	
    _columns = {
        'ref_invoice':fields.many2one('account.invoice',string=u'关联发票'),		
    }
			
    def show_account_delivery(self, cr, uid, ids, context=None):

        act_obj = self.pool.get('ir.actions.act_window')			
        result = act_obj.read(cr, uid, [483], context=context)[0]
        if ids == 0:		
            result['domain'] = "[('state','=','done'), ('ref_invoice','=',False),('picking_type_id','in',[2])]"		
        elif  ids == 1:
            result['domain'] = "[('state','=','done'), ('ref_invoice','!=',False),('picking_type_id','in',[2])]"
			
        return result	
		
    def _invoice_create_line(self, cr, uid, moves, journal_id, inv_type='out_invoice', context=None):
        invoice_obj = self.pool.get('account.invoice')
        move_obj = self.pool.get('stock.move')
        invoices = {}
        _logger.info("Jimmy --- _invoice_create_line in sotck_loewie")		
		
        for move in moves:
            company = move.company_id
            origin = move.picking_id.name
            partner, user_id, currency_id = move_obj._get_master_data(cr, uid, move, company, context=context)

            key = (partner, currency_id, company.id, user_id)
            invoice_vals = self._get_invoice_vals(cr, uid, key, inv_type, journal_id, move, context=context)

            if key not in invoices:
                # Get account and payment terms
                invoice_id = self._create_invoice_from_picking(cr, uid, move.picking_id, invoice_vals, context=context)
                invoices[key] = invoice_id				
                invoice = invoice_obj.browse(cr, uid, [invoice_id], context=context)[0]	
                invoice.write({'picking_id': move.picking_id.id})				
                move.picking_id.ref_invoice = invoice_id				
                _logger.info("Jimmy picking_id:%d" % move.picking_id.id)				
                if move.picking_id.sale_id : 
                    invoice.write({'sale_id': move.picking_id.sale_id.id})				
                    _logger.info("Jimmy sale_id:%d" % move.picking_id.sale_id.id)					
            else:
                invoice = invoice_obj.browse(cr, uid, invoices[key], context=context)
                if not invoice.origin or invoice_vals['origin'] not in invoice.origin.split(', '):
                    invoice_origin = filter(None, [invoice.origin, invoice_vals['origin']])
                    invoice.write({'origin': ', '.join(invoice_origin)})
                invoice.write({'picking_id': move.picking_id.id})					
                _logger.info("Jimmy nokey picking_id:%d" % move.picking_id.id)	
                move.picking_id.ref_invoice = invoice_id				
                if move.picking_id.sale_id : 
                    _logger.info("Jimmy nokey sale_id:%d" % move.picking_id.sale_id.id)                    				
                    invoice.write({'sale_id': move.picking_id.sale_id.id})					

            invoice_line_vals = move_obj._get_invoice_line_vals(cr, uid, move, partner, inv_type, context=context)
            invoice_line_vals['invoice_id'] = invoices[key]
            invoice_line_vals['origin'] = origin

            move_obj._create_invoice_line_from_vals(cr, uid, move, invoice_line_vals, context=context)
            move_obj.write(cr, uid, move.id, {'invoice_state': 'invoiced'}, context=context)

        invoice_obj.button_compute(cr, uid, invoices.values(), context=context, set_total=(inv_type in ('in_invoice', 'in_refund')))
        return invoices.values()	