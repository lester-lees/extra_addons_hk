# -*- coding: utf-8 -*- manager_confirm_btn
from openerp.osv import fields, osv
from openerp.tools.translate import _
import time
from openerp import tools, api
import psycopg2
import datetime
import logging

_logger = logging.getLogger(__name__)

class sale_order(osv.osv):
    _inherit = 'sale.order'
    _name = 'sale.order'
	
    _columns = {
        'total_weight' : fields.float('Total Weight') ,		
    }
	
    def del_lines(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids, context=context)[0]	
		
        for line in this.order_line :
            if line.delete == True:
                line.unlink()	
				
        return	

    def cal_qty_shortage(self, cr, uid, ids, context=None):
        this = self.browse(cr, uid, ids, context=context)[0]	
        products = {}
        statement = """select product_id,sum(product_uom_qty) as qty from sale_order_line where order_id=%d group by product_id""" % ids[0]
        cr.execute(statement)	 
	
        for i in cr.fetchall():	
            products[i[0]] = i[1]	
		
        for line in this.order_line :
            qty = line.qty_on_hand - products[line.product_id.id] - (line.qty_reserved - line.qty_self_reserved) 
            _logger.info("""Jimmy: %d""" % qty)				
            if qty < 0:
                line.shortage = - qty
            if qty >= 0:
                line.shortage = 0			
				
        return		

    def calc_total_weight(self, cr, uid, ids, context=None): #self, cr, uid, ids, name, attr, context=None): 
	
        weight = 0
        this = self.browse(cr, uid, ids, context=context)[0]	
		
        for line in this.order_line :
            weight = weight + line.product_id.weight * line.product_uom_qty		
			
        this.write({'total_weight':weight})			
        return
		
	
    def check_stock(self, cr, uid, ids, context=None):
        if not context:
            context = {}
        		
        if len(ids) > 0:
            created_id = self.pool['sale.order.line'].calc_qty( cr, ids[0] , uid )
        else:
            return {}			
	
        view_ref = self.pool.get('ir.model.data').get_object_reference(cr, uid, 'sale_access_loewie', 'view_check_so_stock')
        view_id = view_ref and view_ref[1] or False,
        self.cal_qty_shortage(cr, uid, ids)
		
        return {
            'name': _('Sales Check Stock'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'view_id': view_id,
            'target': 'new',
            'res_id': ids[0],
            'domain': ['&',('product_id.type','!=','service'),('shortage','>',0)],					
        }			


    def get_discount(self, cr, uid, ids, partner_id = 0, brands='', type='', amount=0, context=None):
	
        statement = """select amount,discount from product_discount where partner_id = %d and  brands = %s and type = %s order by amount desc""" % (partner_id, brands, type)	
        cr.execute(statement)
		
        for i in cr.fetchall():	
            if i.amount	< amount:
                return i.discount
				
        return 0				
        		
		
    def set_discount(self, cr, uid, ids, context=None):	
			
        month = "%d-%d" % (datetime.datetime.now().year, datetime.datetime.now().month)
        statement = """select product_type as brands,sum(price_total) as amount, sum(product_uom_qty) as qty
        from sale_order_line sol left join product_product pp on sol.product_id = pp.id 
        where sol.name != 'Promotion' and sol.name != 'Shortage' and sol.name != 'Sample' and 
        order_id in (select id from sale_order where date_confirm >= %s-1 and date_confirm < %s-1 and partner_id = %d and state != 'cancel') 
        group by product_type""" % (month,month,partner_id)
		
        cr.execute(statement)
        brands_amount_qty = {}		
        for i in cr.fetchall():
            brands_amount_qty[i.brands] = { 'amount':i.amount, 'qty':i.qty}
	
        this = self.browse(cr, uid, ids, context=context)[0]	
        brands_discount = {}	
        for key in brands_amount_qty.keys():
            brands_discount[key] = get_discount( cr, uid, ids, partner_id=this.parter_id.id, brands=key, type='amount', amount = brands_amount_qty[key]['amount'])	
		
        for line in this.order_line :
            if line.name != '' and line.name != '' and line.name != '' and line.product_id.product_type in brands_discount.getKeys():
                line.discount = brands_discount[line.product_id.product_type]	
			
        return {}
	
		
	

class sale_order_line(osv.osv):
    _inherit = 'sale.order.line'
    _name = 'sale.order.line'

    def _calc_shortage(self, cr, uid, ids, name, attr, context=None):
        context = dict(context or {})	
        res = {}	
        for m in self.browse(cr, uid, ids, context=context):		
            res[m.id] = m.product_uom_qty + m.qty_reserved - m.qty_on_hand			
        return res		
		
    _columns = {	
        'qty_on_hand': fields.integer('Quantity On Hand', default=0 , readonly=True),		
        'qty_standby': fields.integer('Quantity Standby', default=0, readonly=True ),		
        'qty_reserved': fields.integer('Total Reserved', default=0, readonly=True ),
        'qty_self_reserved': fields.integer('Qty Reserved For this Order(Can Ship)', default=0, readonly=True ),
        'qty_on_the_way': fields.integer('Quantity On the way', default=0, readonly=True ),
        'shortage': fields.integer('Shortage of this Order', default=0 , readonly=True),	
        'delete':fields.boolean('Delete ?',default=False),		
    }        	
	
    def calc_qty(self, cr, order_id = None, uid = None):    	
        if order_id == None : 
            return {}			
		
        statement = """ 
        update sale_order_line sol set qty_on_hand = (select sum(qty) from stock_quant where product_id=sol.product_id and location_id in (select id from stock_location where usage='internal' and scrap_location = False)) where order_id=%d;		
        update sale_order_line set qty_on_hand = 0 where qty_on_hand is Null and order_id=%d;

        update sale_order_line sol set qty_reserved = (select sum(qty) from stock_quant where product_id=sol.product_id and reservation_id is not Null and location_id in (select id from stock_location where usage='internal' and scrap_location = False)) where order_id=%d;		
        update sale_order_line set qty_reserved = 0 where qty_reserved is Null and order_id=%d;

        update sale_order_line sol set qty_self_reserved = (select sum(qty) from stock_quant where product_id=sol.product_id and reservation_id is not Null and reservation_id in ( select id from stock_move where (name like (select name from sale_order where id=%d) || '%s' or origin like (select name from sale_order where id=%d)|| '%s') ) and location_id in (select id from stock_location where usage='internal' and scrap_location = False)) where order_id=%d;
		update sale_order_line set qty_self_reserved = 0 where qty_self_reserved is Null and order_id=%d;		
		"""	% ( order_id, order_id, order_id, order_id, order_id, '%', order_id, '%', order_id, order_id )	
		
        cr.execute(statement)		
