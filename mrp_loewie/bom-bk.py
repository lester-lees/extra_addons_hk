# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import datetime
import logging
import xmlrpclib
import urllib2

_logger = logging.getLogger(__name__)
		
class RedirectHandler(urllib2.HTTPRedirectHandler):
    def http_error_301(self, req, fp, code, msg, headers):
        pass
    def http_error_302(self, req, fp, code, msg, headers):
        pass		
		
class stock_move(osv.osv):
    _inherit = "stock.move"

    _columns = {
        'produce_bill': fields.many2one('loewie.production', 'Produce Bill'),	
    }
	
class loewie_bom(osv.osv):
    _name = "loewie.bom"
    _description = "Loewie Bill of Materials"	
	
    _columns = {
        'parent_id': fields.many2one('product.product','Parent Proudct'),	
        'product_id': fields.many2one('product.product','Child Proudct'),
        'name': fields.char('Description'),
        'qty_need': fields.float('Child Quantity',default=1),
        #'produce_bill': fields.many2one('loewie.production', 'Produce Bill'),		
    }		
	
	
    def do_something_special(self, cr, uid, ids, context=None ):
        #opener = urllib2.build_opener(RedirectHandler)
        #opener.open('http://192.168.0.200:8069/web#id=3439&view_type=form&model=stock.picking&action=162&active_id=1')		
        #response = urllib2.urlopen('http://192.168.0.200:8069/web#id=3439&view_type=form&model=stock.picking&action=162&active_id=1')	
        #redirected = response.geturl() == 'http://192.168.0.200:8069/web#id=3439&view_type=form&model=stock.picking&action=162&active_id=1'
		
        return {
            'type':'ir.actions.act_url',
            'url':'http://192.168.0.200:8069/web#id=3439&view_type=form&model=stock.picking&action=162&active_id=1',
            'target':'new',			
        }
        """
        db = "LoewieSZ"	
        pwd = "Ufesbdr$%HG&hgf2432"		
        user = "admin"		
        model = "stock.picking"		
        method = "read"		
        pids = [3123,3124,3125]		
        fields = ['name','id','state','note']		
	
        proxy = xmlrpclib.ServerProxy("http://192.168.0.200:8069/xmlrpc/object")	
        values = proxy.execute(db, 1, pwd,model,method, pids, fields ) 		
		
        for bom in self.browse(cr, uid, ids, context=context):
            bom.name = 	values[1]['name']	
        """
			
			
        """	
        stock_picking = self.pool.get('stock.picking')	
        pick_ids = 	stock_picking.search(cr, uid, [], context=context)	
        		
        for pick in stock_picking.browse(cr, uid, pick_ids, context=context):

            if pick.sale_id : 
                #pick.partner_id = pick.sale_id.partner_id.id
                continue				
				
            #if pick.purchase_order : 
            #    pick.partner_id = pick.purchase_order.partner_id.id		
			
            warehouse, direction , number = invoice.origin.split('\\')
            if direction == 'OUT' : 
                direction = 'outgoing'
            elif direction == 'IN' : 
                direction = 'incoming'	
        				

        invoice_ids = self.pool.get('account.invoice').search(cr, uid, [], context=context)
        pickings = self.pool.get('stock.picking')
		
        for invoice in self.pool.get('account.invoice').browse(cr, uid, invoice_ids, context=context):
            if invoice.sale_id or invoice.picking_id : continue


            pid = pickings.search(cr, uid, [('name','=',invoice.origin)], context=context)
            if len(pid) < 1: continue			
            pobj = pickings.browse(cr, uid, pid, context=context)[0]
            invoice.sale_id = pobj.sale_id.id			
            invoice.picking_id = pobj.id
		
        return		
        """	
		
class loewie_production(osv.osv):
    _name = "loewie.production"
    _description = "Loewie Produce Bill"

    _columns = {	
        'product_id': fields.many2one('product.product','Proudct',required=True, readonly=True, states={'draft': [('readonly', False)]}),		
        'produce_qty': fields.float('Produce Quantity',default=1,required=True, readonly=True, states={'draft': [('readonly', False)]}),		
        'produce_lines' : fields.one2many('stock.move', 'produce_bill', 'Stock Moves', readonly=True, states={'draft': [('readonly', False)]}),
        'state' : fields.selection([('cancel', 'Cancel'),('draft', 'Draft'),('expanded','Expanded'), ('confirm', 'Confirm'), ('done', 'Done')], string='Status', readonly=True, copy=False, default='draft'),
        'note' : fields.text('Description', states={'done': [('readonly', True)]}),
        'date_start' : fields.date(string='Start Date', default=fields.date.today(), readonly=True, states={'draft': [('readonly', False)]}),	
        'date_finish' : fields.date(string='Finish Date', readonly=True),	
    }
	
    def expand_produce(self, cr, uid, ids, context=None ):
	
        loewie_boms = self.pool.get('loewie.bom')
        stock_moves = self.pool.get('stock.move')	
		
        vals = {
            'produce_bill':0,		
            'product_id':0, 
            'product_uom_qty':0, 
            'location_dest_id':7, 
            'location_id':12, 
            'company_id':1, 
            'date':datetime.date.today(),
            'date_expected':datetime.date.today() + datetime.timedelta(3), 
            'invoice_state':'none', 
            'name':'Produce Bill', 
            'procure_method':'make_to_stock', 
            'product_uom':0, 
            'weight_uom_id':0,
        }    		

        #_logger.info("Jimmy : in start produce")		
		
        for pbill in self.browse(cr, uid, ids, context=context):
		
            bom_ids = loewie_boms.search(cr, uid, [('parent_id', '=', pbill.product_id.id)], context=context)
            if len(bom_ids) < 1 : continue			
			
            for move in pbill.produce_lines:
                move.unlink()			
			
            for products in loewie_boms.browse(cr, uid, bom_ids, context=context):
                vals.update({'produce_bill':pbill.id, 'product_id':products.product_id.id,'product_uom_qty':products.qty_need * pbill.produce_qty, 'product_uom':products.product_id.uom_po_id.id,'weight_uom_id':products.product_id.uom_po_id.id}) 			
                stock_moves.create(cr, uid, vals, context=context)
				
            vals.update({'location_id':7,'location_dest_id':12,'produce_bill':pbill.id, 'product_id':pbill.product_id.id,'produce_qty':pbill.produce_qty, 'product_uom':pbill.product_id.uom_po_id.id,'weight_uom_id':pbill.product_id.uom_po_id.id})
            stock_moves.create(cr, uid, vals, context=context)
				
            pbill.state = 'expanded'
			
        return	
	
    def confirm_produce(self, cr, uid, ids, context=None ):
	
        for pbill in self.browse(cr, uid, ids, context=context):

            for move in pbill.produce_lines:
                move.action_confirm()			
				
            pbill.state = 'confirm'		
			
        return
	
    def start_produce(self, cr, uid, ids, context=None ):
	
        for pbill in self.browse(cr, uid, ids, context=context):

            for move in pbill.produce_lines:
                move.action_done()			
				
            pbill.state = 'done'				
        return		

    def set_to_draft(self, cr, uid, ids, context=None ):
	
        for pbill in self.browse(cr, uid, ids, context=context):

            for move in pbill.produce_lines:
                move.action_cancel()			
                move.unlink()			
				
            pbill.state = 'draft'				
        return			
		
		
    def cancel_produce(self, cr, uid, ids, context=None ):
	
        for pbill in self.browse(cr, uid, ids, context=context):

            for move in pbill.produce_lines:
                move.action_cancel()			
                move.unlink()			
				
            pbill.state = 'draft'				
        return			