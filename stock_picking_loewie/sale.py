# -*- coding: utf-8 -*- manager_confirm_btn
from openerp.osv import fields, osv
import csv
import cStringIO
import base64
import psycopg2
from openerp.tools.translate import _
import logging
from openerp.tools.float_utils import float_round

_logger = logging.getLogger(__name__)

class product_product(osv.osv):
    _inherit = "product.product"
	
    def _qty_avail(self, cr, uid, ids, field_names=None, arg=False, context=None):
        context = context or {}
        field_names = field_names or []

        domain_products = [('product_id', 'in', ids)]
        domain_quant, domain_move_in, domain_move_out = self._get_domain_locations(cr, uid, ids, context=context)
        domain_quant += domain_products
        if context.get('lot_id') or context.get('owner_id') or context.get('package_id'):
            if context.get('lot_id'):
                domain_quant.append(('lot_id', '=', context['lot_id']))
            if context.get('owner_id'):
                domain_quant.append(('owner_id', '=', context['owner_id']))
            if context.get('package_id'):
                domain_quant.append(('package_id', '=', context['package_id']))

        domain_qty_avail_ec = [('location_id', '=', 35),('reservation_id','=',False)] + domain_products	
        quants_qty_avail_ec = self.pool.get('stock.quant').read_group(cr, uid, domain_qty_avail_ec, ['product_id', 'qty'], ['product_id'], context=context)
        quants_qty_avail_ec = dict(map(lambda x: (x['product_id'][0], x['qty']), quants_qty_avail_ec))
		
        domain_qty_onhand_ec = [('location_id', '=', 35)] + domain_products		
        quants_qty_onhand_ec = self.pool.get('stock.quant').read_group(cr, uid, domain_qty_onhand_ec, ['product_id', 'qty'], ['product_id'], context=context)
        quants_qty_onhand_ec = dict(map(lambda x: (x['product_id'][0], x['qty']), quants_qty_onhand_ec))
				
        quants = self.pool.get('stock.quant').read_group(cr, uid, domain_quant, ['product_id', 'qty'], ['product_id'], context=context)
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))

        domain_quant_avail = domain_quant + [('reservation_id','=',False)]			
        quants_avail = self.pool.get('stock.quant').read_group(cr, uid, domain_quant_avail, ['product_id', 'qty'], ['product_id'], context=context)
        quants_avail = dict(map(lambda x: (x['product_id'][0], x['qty']), quants_avail))
		
        res = {}
        for product in self.browse(cr, uid, ids, context=context):
            id = product.id
            qty_avail_store	= product.qty_avail_store	
			
            qty_avail = float_round(quants_avail.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            quants_all = float_round( quants.get(id, 0.0), precision_rounding=product.uom_id.rounding )			
            qty_avail_ec = float_round(quants_qty_avail_ec.get(id, 0.0), precision_rounding=product.uom_id.rounding)
            qty_onhand_ec = float_round(quants_qty_onhand_ec.get(id, 0.0), precision_rounding=product.uom_id.rounding)
			
            if qty_avail_store != qty_avail : product.qty_avail_store = qty_avail			
			
            res[id] = {
                'qty_avail': qty_avail,
                'qty_avail_ec': qty_avail_ec,
                'qty_onhand_ec': qty_onhand_ec,
                'qty_onhand_total': qty_onhand_ec + quants_all,			
            }			
			
        return res
	
		
    def _search_product_qty(self, cr, uid, obj, name, domain, context):
        res = []
        for field, operator, value in domain:
            #to prevent sql injections
            assert field in ('qty_avail', 'qty_avail_ec', 'qty_onhand_ec', 'qty_onhand_total'), 'Invalid domain left operand'
            assert operator in ('<', '>', '=', '!=', '<=', '>='), 'Invalid domain operator'
            assert isinstance(value, (float, int)), 'Invalid domain right operand'

            if operator == '=':
                operator = '=='

            product_ids = self.search(cr, uid, [], context=context)
            ids = []
            if product_ids:
                #TODO: use a query instead of this browse record which is probably making the too much requests, but don't forget
                #the context that can be set with a location, an owner...
                for element in self.browse(cr, uid, product_ids, context=context):
                    if eval(str(element[field]) + operator + str(value)):
                        ids.append(element.id)
            res.append(('id', 'in', ids))
        return res
		
    _columns = {	
        'qty_alarm': fields.integer(u'电商警戒数量', default=0),	
        'clean_inventory': fields.boolean(u'Is清库存产品?', default=False, help="Clean the Inventory of this product."),
        'is_materials': fields.boolean(u'Is包材配件?', default=False, help="Is Packaging Materials."),			
        'is_sample': fields.boolean(u'Is样品?', default=False, help="Is Sample."),	
        'is_market': fields.boolean(u'Is市场物资', default=False, help="Is Market Materials."),
        'is_clean_inventory': fields.boolean(u'Is 清库存', default=False, help="清库存产品"),		
        'is_sell_on_ec': fields.boolean(u'Is电商销售的产品?', default=False, help="Is Selling on TMall and JD."),			
        'qty_avail_store': fields.float(string=u'可用库存2', default=0 ),		
        'qty_avail': fields.function(_qty_avail, type='float',string=u"可用库存", multi='qty_avail',fnct_search=_search_product_qty),	
        'qty_avail_ec': fields.function(_qty_avail, type='float',string=u"电商 可用库存", multi='qty_avail',fnct_search=_search_product_qty),		
        'qty_onhand_ec': fields.function(_qty_avail, type='float',string=u"电商 在手库存", multi='qty_avail',fnct_search=_search_product_qty),
        'qty_onhand_total': fields.function(_qty_avail, type='float',string=u"总计 在手库存", multi='qty_avail',fnct_search=_search_product_qty),		
    }

class sale_order(osv.osv):
    _inherit = 'sale.order'	

    def set_order_line_status(self, cr, uid, ids, status, context=None):
        line = self.pool.get('sale.order.line')
        order_line_ids = []
        proc_obj = self.pool.get('procurement.order')
        for order in self.browse(cr, uid, ids, context=context):
            order_line_ids += [po_line.id for po_line in order.order_line]
        if order_line_ids:
            line.write(cr, uid, order_line_ids, {'state': status}, context=context)
        if order_line_ids and status == 'cancel':
            procs = proc_obj.search(cr, uid, [('sale_line_id', 'in', order_line_ids)], context=context)
            if procs:
                proc_obj.write(cr, uid, procs, {'state': 'exception'}, context=context)
        return True	

    def action_cancel_draft(self, cr, uid, ids, context=None):
        if not len(ids):
            return False
        self.write(cr, uid, ids, {'state':'draft','shipped':0})
        self.set_order_line_status(cr, uid, ids, 'draft', context=context)
        for p_id in ids:
            # Deleting the existing instance of workflow for PO
            self.delete_workflow(cr, uid, [p_id]) # TODO is it necessary to interleave the calls?
            self.create_workflow(cr, uid, [p_id])
			
        this = self.browse(cr, uid, ids[0], context=context)			
		
        if this.procurement_group_id:			
            for line in this.procurement_group_id.procurement_ids:		
                line.unlink()
            this.procurement_group_id.unlink()					
        return True	
	
    #@api.one	
    def calc_total_weight(self, cr, uid, ids, context=None): #self, cr, uid, ids, name, attr, context=None): 
	
        weight = 0
        this = self.browse(cr, uid, ids, context=context)[0]	
		
        for line in this.order_line :
            weight = weight + line.product_id.weight * line.product_uom_qty		
			
        this.write({'total_weight':weight})	
		
        return
			
    _columns = {
        'upload_file':fields.binary('Up&Download Order Lines'),	
        'total_weight' : fields.float('Total Weight') ,		
        'state': fields.selection([
            ('draft', 'Draft Quotation'),
            ('sent', 'Quotation Sent'),
            ('manager_confirm','Manager Confirm'),			
            ('cancel', 'Cancelled'),
            ('waiting_date', 'Waiting Schedule'),
            ('progress', 'Sales Order'),
            ('manual', 'Sale to Invoice'),
            ('shipping_except', 'Shipping Exception'),
            ('invoice_except', 'Invoice Exception'),
            ('done', 'Done'),
            ], 'Status', readonly=True, copy=False, help="Gives the status of the quotation or sales order.\
              \nThe exception status is automatically set when a cancel operation occurs \
              in the invoice validation (Invoice Exception) or in the picking list process (Shipping Exception).\nThe 'Waiting Schedule' status is set when the invoice is confirmed\
               but waiting for the scheduler to run on the order date.", select=True),
        'country_id': fields.related('partner_id', 'country_id', type='many2one', relation='res.country', string='Country'),			   
    }
	
    def inform_warehouse_shipping(self, cr, uid, ids, context=None):	
        for so in self.browse(cr, uid, ids, context=context):
            for pick in so.picking_ids:
                if pick.state == 'assigned'	and pick.can_ship == False : pick.can_ship = True
				
        return True			
		
    #@api.one	
    def export_csv(self, cr, uid, ids, context=None):

        this = self.browse(cr, uid, ids, context=context)[0]	
        buf = cStringIO.StringIO()
        writer = csv.writer(buf)		
		
        for line in this.order_line:
            writer.writerow([line.product_id.id,line.name,line.product_uom_qty,line.price_unit,line.product_uom.id])		
			
        out = base64.encodestring(buf.getvalue())
        this.write({'upload_file':out})	
		
        return		

    #@api.one		
    def import_csv(self, cr, uid, ids, context=None):
	
        this = self.browse(cr, uid, ids, context=context)[0]
        sol_obj = self.pool.get('sale.order.line')		#sol_obj: sale.order.line
        buf = cStringIO.StringIO(base64.decodestring(this.upload_file))
        reader = csv.reader(buf)		
		
        for line in reader:            		
            statement = "insert into sale_order_line(order_id,product_id,name,product_uom_qty,price_unit,product_uom,delay,state) values(%d,%s,'%s',%s,%s,%s,7,'draft')" % ( this.id, line[0], line[1], line[2], line[3], line[4])			
            cr.execute(statement)			
		
        for line in this.order_line:
            vals = sol_obj.product_id_change(
                cr, uid, line.id, this.pricelist_id.id,
                product=line.product_id.id, qty=line.product_uom_qty,
                uom=line.product_uom.id, qty_uos=line.product_uos_qty,
                uos=line.product_uos.id, name=line.name,
                partner_id=this.partner_id.id,
                lang=False, update_tax=True, date_order=this.date_order,
                packaging=False, fiscal_position=False, flag=False, context=context)
            sol_obj.write(cr, uid, line.id, vals['value'], context=context)            		
			
        return			

    def onchange_pricelist_id(self, cr, uid, ids, pricelist_id, order_lines, context=None):
        context = context or {}
        if not pricelist_id:
            return {}
        pricelist_obj = self.pool.get('product.pricelist')
        pricelist_this_obj = pricelist_obj.browse(cr, uid, pricelist_id, context=context)		
        value = {
            'currency_id': pricelist_this_obj.currency_id.id
        }
        if not order_lines or order_lines == [(6, 0, [])]:
            return {'value': value}

        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(cr, uid, 'Account')
        currency_obj = self.pool.get('res.currency')		
        this = self.browse(cr, uid, ids, context=context)[0]		
		
        for line in this.order_line:
            line.pur_currency_id = line.product_id.purchase_currency_id.id		
			
            #line.pur_price_unit = round(pricelist_obj.price_get(cr, uid, [pricelist_id], line.product_id.id, 1.0, this.partner_id.id,{'uom': line.product_uom.id, 'date': this.date_order})[pricelist_id], prec)		
            
            #if line.pur_price_unit == 0 and pricelist_this_obj.use_purchase_currency :
            line.pur_price_unit = line.get_price( pricelist_id, line.product_id.id)	
				
            if pricelist_this_obj.use_purchase_currency :
                line.price_unit = 	currency_obj.compute(cr, uid, line.pur_currency_id.id, value['currency_id'],line.pur_price_unit, context=context)	
            else:
                line.price_unit = line.pur_price_unit
				
            line.subtotal = round(line.price_unit * line.product_uom_qty / (100 - line.discount)*100 ,prec)
		
			
        warning = {
            'title': _('Pricelist Warning!'),
            'message' : _('If you change the pricelist of this order (and eventually the currency), prices of existing order lines will not be updated.')
        }
        return {'warning': warning, 'value': value}	
			
    def action_view_delivery(self, cr, uid, ids, context=None):
 
        for so in self.browse(cr, uid, ids, context=context):
            is_tmall_jd = so.partner_id.name
            is_tmall_jd = ( is_tmall_jd.find('TMI')>=0 or is_tmall_jd.find('JDI')>=0 )	
            user = so.user_id and so.user_id.id or so.create_uid.id			
            			
            for pick in so.picking_ids:
                #if is_tmall_jd and pick.state != 'done' : pick.move_lines.filtered(lambda r: r.location_id.id != 35).write({'location_id':35})	
				
                pick.add_followers({'ids':[pick.id], 'user_ids':[user]}, context=context)
                pick.create_uid = user	
                if pick.state in ['confirmed'] :
                    statement = "update ir_attachment set res_id=%d, res_model='stock.picking', res_name='%s' where res_id=%d and datas_fname like '%s.xlsx'" % ( pick.id, pick.name, so.id, '%' )
                    cr.execute(statement)						
                    pick.action_assign()	
						
                for line in pick.move_lines:					
                    if line.name and line.name.find('RMA')>=0 and line.state != 'done':			
                        line.location_id = 20 # Standby Location ID = 20      
        
        return super(sale_order, self).action_view_delivery(cr, uid, ids, context=None)
		