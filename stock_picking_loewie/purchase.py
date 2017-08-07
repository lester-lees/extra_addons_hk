# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import csv
import cStringIO
import base64
import psycopg2
import datetime

class purchase_order(osv.osv):
    _inherit = "purchase.order"
    _name = "purchase.order"
	
    STATE_SELECTION = [
        ('draft', 'Draft PO'),
        ('sent', 'RFQ'),
        ('manager_confirm','Manager Confirm'),		
        ('bid', 'Bid Received'),
        ('confirmed', 'Waiting Approval'),
        ('approved', 'Purchase Confirmed'),
        ('except_picking', 'Shipping Exception'),
        ('except_invoice', 'Invoice Exception'),
        ('done', 'Done'),
        ('cancel', 'Cancelled')
    ]

    _columns = {
        'upload_file':fields.binary('Up&Download Order Lines'),		
        'state': fields.selection(STATE_SELECTION, 'Status', readonly=True,
                                  help="The status of the purchase order or the quotation request. "
                                       "A request for quotation is a purchase order in a 'Draft' status. "
                                       "Then the order has to be confirmed by the user, the status switch "
                                       "to 'Confirmed'. Then the supplier must confirm the order to change "
                                       "the status to 'Approved'. When the purchase order is paid and "
                                       "received, the status becomes 'Done'. If a cancel action occurs in "
                                       "the invoice or in the receipt of goods, the status becomes "
                                       "in exception.",
                                  select=True, copy=False),
    }
	
    def export_csv(self, cr, uid, ids, context=None):

        this = self.browse(cr, uid, ids, context=context)[0]	
        buf = cStringIO.StringIO()
        writer = csv.writer(buf)		
		
        for line in this.order_line:
            writer.writerow([line.product_id.id,line.name,line.product_qty,line.price_unit,line.product_uom.id])		
			
        out = base64.encodestring(buf.getvalue())
        this.write({'upload_file':out})	
		
        return		

    #@api.one		
    def import_csv(self, cr, uid, ids, context=None):
	
        this = self.browse(cr, uid, ids, context=context)[0]
        sol_obj = self.pool.get('purchase.order.line')		#sol_obj: sale.order.line
        buf = cStringIO.StringIO(base64.decodestring(this.upload_file))
        reader = csv.reader(buf)
		
        conn_string = "host='localhost' dbname='LoewieHK' user='postgres' password='postgres'"
        conn = psycopg2.connect(conn_string)
        cursor = conn.cursor()		
		
        for line in reader:            		
            statement = "insert into purchase_order_line(order_id,product_id,name,product_qty,price_unit,product_uom,date_planned,state) values(%d,%s,'%s',%s,%s,%s,'%s','draft')" % ( this.id, line[0], line[1], line[2], line[3], line[4],datetime.date.today().strftime("%m/%d/%Y"))			
            cursor.execute(statement)
            conn.commit()			          		
			
        return		
		
		
    def view_picking(self, cr, uid, ids, context=None):
        if context is None:
            context = {}

        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            for picking in po.picking_ids:
                picking.create_uid = po.create_uid.id		

        return super(purchase_order, self).view_picking(cr, uid, ids, context=None)		