# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import datetime
import logging
import xmlrpclib
import urllib2

_logger = logging.getLogger(__name__)

class loewie_sqlstatement(osv.osv):
    _name = "loewie.sqlstatement"
    _description = "Loewie Sql Statement"		
	
    _columns = {
        'name': fields.char('Name'),	
        'statement': fields.text('Sql Statement'),	
        'result': fields.text('Result'),
        'remark': fields.text('Remark'),		
    }				

    def do_sql_execute(self, cr, uid, ids, context=None):
        sql_obj = self.browse(cr, uid, ids, context=context)	
        sql_statement = context.get('statement',False) or sql_obj.statement
		
        if not sql_statement : return 

        cr.execute(sql_statement)
        res = cr.fetchall()
        res_txt = ''	
        if not res : return
		
        for line in res:
            first = True		
            for item in line:
                if not first : 
                    res_txt += chr(9) + str(item)
                else: 
                    res_txt += str(item)
                    first = False					
            res_txt += chr(10)
			
        sql_obj.write({'result':res_txt})		
        	
	
class stock_move(osv.osv):
    _inherit = "stock.move"

    _columns = {
        'produce_bill': fields.many2one('loewie.production', 'Produce Bill'),	
    }
	
	
class loewie_bom(osv.osv):
    _name = "loewie.bom"
    _description = "Loewie Bill of Materials"	
    _db = "LoewieSZ"	
    _pwd = "Ufesbdr$%HG&hgf2432"	
	
    _columns = {
        'parent_id': fields.many2one('product.product','Parent Proudct'),	
        'product_id': fields.many2one('product.product','Child Proudct'),
        'name': fields.char('Description'),
        'qty_need': fields.float('Child Quantity',default=1),
        #'produce_bill': fields.many2one('loewie.production', 'Produce Bill'),		
    }		
	
	
    def do_something_special(self, cr, uid, ids, context=None ):
	
        vals_pick = {
            'company_id': 1, #self.query_id_byname('res.company',u'深圳市乐易保健用品有限公司'),
            'partner_id': 1058, #self.query_id_byname('res.partner',u'Loewie香港有限公司'), 	
            'create_date': '2016-06-14 08:50:00', #datetime.date.today().strftime("%Y-%M-%d %H:%M:%S"),			
            'origin': 'HK-PO',			
            #'invoice_state': 'none',			
            'move_type': 'direct',
            'picking_type_id': 1, #self.query_id_byname('stock.picking.type','Receipts(收货)'),			
            #'priority': 1,		
            #'weight_uom_id': 3,            			
        }		
	
        vals_move = {	
            'product_id': 0, #, 
            'product_uom_qty':0, 
            'location_dest_id':self.query_id_byname('stock.location', u'成品'), 
            'location_id':self.query_id_byname('stock.location', 'Suppliers'), 
            'company_id':self.query_id_byname('res.company',u'深圳市乐易保健用品有限公司'), 
            'date':datetime.date.today().strftime("%Y-%M-%d %H:%M:%S"),
            'date_expected':(datetime.date.today() + datetime.timedelta(3)).strftime("%Y-%M-%d %H:%M:%S"), 
            'invoice_state':'none', 
            'name':'.', 
            'procure_method':'make_to_stock', 
            'product_uom':1, 
            'weight_uom_id':1,
        }	
	
        model1 = "stock.picking"		
        model2 = "stock.move"		
        method = "create" 		
	
	
        my_proxy = xmlrpclib.ServerProxy("http://192.168.0.200:8069/xmlrpc/object")		
			
        value = my_proxy.execute(self._db, 1, self._pwd, model1,method, vals_pick )
        remote_picking_id = value		

		
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
            'product_uom':1, 
            'weight_uom_id':1,
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
				
            #vals.update({'location_id':7,'location_dest_id':12,'produce_bill':pbill.id, 'product_id':pbill.product_id.id,'produce_qty':pbill.produce_qty, 'product_uom':pbill.product_id.uom_po_id.id,'weight_uom_id':pbill.product_id.uom_po_id.id})
            #stock_moves.create(cr, uid, vals, context=context)
				
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