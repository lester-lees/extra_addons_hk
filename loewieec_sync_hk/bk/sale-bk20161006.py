# -*- encoding: utf-8 -*-
from openerp.osv import fields,osv

class product_tmalljd(osv.osv):
    _name = "product.tmalljd"
    #_inherits = {'product.product': 'product_id'}

    def _get_ean13(self, cr, uid, ids, field_name, arg, context=None):	
        result = {}
        for line in self.pool.get('product.tmalljd').browse(cr, uid, ids, context=context):
            if line.erp_product_id : result[line.id] = line.erp_product_id.ean13 or line.erp_product_id.default_code
        return result		

    def _get_stock(self, cr, uid, ids, field_name, arg, context=None):	
        result = {}
        domain_products = [('location_id','=',38)]		
        quants = self.pool.get('stock.quant').read_group(cr, uid, domain_products, ['product_id', 'qty'], ['product_id'], context=context)	
        quants = dict(map(lambda x: (x['product_id'][0], x['qty']), quants))
		
        for line in self.pool.get('product.tmalljd').browse(cr, uid, ids, context=context):
            id = line.id
            if line.erp_product_id :
                pid = line.erp_product_id.id			
                result[id] = quants.get(pid, 0.0)
            else:
                result[id] = 0			
        return result		
		
    _columns = {
        'erp_product_id': fields.many2one('product.product','ERP Name'),
        'erp_ean13': fields.char('ERP_EAN13'), #fields.function(_get_ean13,type='char',string='ERP_EAN13'),
        'erp_stock': fields.float('ERP_Stock'),#fields.function(_get_stock,type='float',string='ERP库存'),		
        'ec_shop_id': fields.many2one('loewieec.shop', u'店铺'),		
        'ec_num_iid': fields.char(u'电商数字编码'),
        'ec_sku_id': fields.char(u'SKU编码'),
        'ec_title':fields.char(u'商品标题'),
        'ec_price':fields.float(u'售价'),
        'ec_color':fields.char(u'颜色'),
        'ec_ean13': fields.char(u'条形码'),
        'ec_brand': fields.char(u'品牌'),
        'ec_qty': fields.integer(u'EC数量'),
        'ec_outer_code': fields.char(u'商家外部编码'),		
        'ec_product_name': fields.char(u'产品名称'),	
        'ec_product_id': fields.char(u'EC产品ID'),		
        'ec_num_custom':fields.char(u'海关代码'),	
    }
	
class loewieec_error(osv.osv):
    _name = "loewieec.error"

    _columns = {	
        'shop_id': fields.many2one('loewieec.shop', u'店铺'),
        'name': fields.char(u'错误信息'),
    }

	
class sale_order(osv.osv):
    _name = "sale.order"
    _inherit = "sale.order"
        
    _columns = {	
        'selected': fields.boolean('Selected'),	
        'shop_id': fields.many2one('loewieec.shop', string=u"EC店铺名", readonly=True),
        'sale_code': fields.char(u'EC单号', readonly=True),	
        'tid': fields.char(u'交易单号', readonly=True),	
        'buyer_nick': fields.char(u'买家昵称'),		
        'order_state': fields.selection([
            ('WAIT_SELLER_SEND_GOODS', u'等待卖家发货'),
            ('WAIT_BUYER_CONFIRM_GOODS', u'等待买家确认收货'),
            ('TRADE_FINISHED', u'交易成功'),
            ('TRADE_CLOSED', u'交易关闭'),
            ], u'订单状态'),
    }
	
    def update_waybill_no(self, cr, uid, ids, context=None):
        sale_order_obj = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)	
        shop = sale_order_obj.shop_id		
        if not shop : return False  

        return shop.set_losgistic_confirm(context=context, salesorder=sale_order_obj)			
	
    def view_express_data(self, cr, uid, ids, context=None):	
        sale_order_obj = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)		
        if not sale_order_obj : 
            raise osv.except_osv(u'Sale order 错误',u'''请先保存销售单草稿''')	
            return False

        sale_order_line_ids = self.pool.get('sale.order.line').search(cr,uid,[('order_id','=',ids[0])],context=context)	
        if len(sale_order_line_ids)< 1: return False		
        eids = self.pool.get('sale.order.line').read(cr,uid,sale_order_line_ids,['coe_no'],context=context)	
        express_ids = [ eid['coe_no'] and eid['coe_no'][0] for eid in eids ]			
		
        customer_id = sale_order_obj.partner_id.id
        sale_coe_obj = self.pool.get('sale.coe')
        platform = sale_order_obj.shop_id.code		
        if len(express_ids)>0:		
            for express_obj in sale_coe_obj.browse(cr,uid,express_ids,context=context):
                express_obj.sale_id = ids[0]		
                express_obj.customer = customer_id	                		
		
        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'loewieec_sync_hk', 'action_loewieec_salecoe')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = [('id','in',express_ids)]
        result['res_id'] = express_ids
        result['context'] = {'default_sale_id':ids[0],'default_customer':customer_id}		
		
        return result
	
class sale_coe(osv.osv):
    _name = "sale.coe"	
	
    _columns = {	
        'sale_id': fields.many2one('sale.order', string='Sales Order'),
        'picking_id': fields.many2one('stock.picking',string='Picing Order'),		
        'customer': fields.many2one('res.partner',string=u'客户'),		
        'tmi_jdi_no': fields.char(string='TMI JDI NO'),		
        'name':fields.char(string='COE NO'),	
        'receive_name': fields.char(string='Receive Name'),		
        'tel': fields.char(string='Cell Phone'),
        'state': fields.char(string='State'),	
        'city': fields.char(string='City'),	
        'address': fields.char(string='Address'),	
        'zip': fields.char(string='Zip'),
        'weight': fields.float(string='Weight',default=1),		
        'price': fields.float(string='Fee',default=50),		
    }

class stock_picking(osv.osv):
    _inherit = "stock.picking"
	
    def view_express_data(self, cr, uid, ids, context=None):	
        stock_picking_obj = self.pool.get('stock.picking').browse(cr,uid,ids[0],context=context)	
        if not stock_picking_obj.sale_id : 
            raise osv.except_osv(u'stock.picking 错误',u'''没有销售单与此仓库单有关联''')	
            return False
			
        order_id = 	stock_picking_obj.sale_id.id
        partner_id = stock_picking_obj.partner_id.id 		
        sale_order_line_ids = self.pool.get('sale.order.line').search(cr,uid,[('order_id','=',order_id)],context=context)	
        if len(sale_order_line_ids)< 1: return False		
        eids = self.pool.get('sale.order.line').read(cr,uid,sale_order_line_ids,['coe_no'],context=context)
        express_ids = [ eid['coe_no'] and eid['coe_no'][0] for eid in eids ]			
        if len(express_ids) < 1: 			
            raise osv.except_osv(u'stock.picking 错误',u'''没有快递信息''')		
            return False			
	
        sale_coe_obj = self.pool.get('sale.coe')
        for express_obj in sale_coe_obj.browse(cr,uid,express_ids,context=context):
            if not express_obj.picking_id: 
                express_obj.picking_id = ids[0]		

        mod_obj = self.pool.get('ir.model.data')
        act_obj = self.pool.get('ir.actions.act_window')

        result = mod_obj.get_object_reference(cr, uid, 'loewieec_sync_hk', 'action_loewieec_salecoe')
        id = result and result[1] or False
        result = act_obj.read(cr, uid, [id], context=context)[0]
        result['domain'] = [('id','in', express_ids)]
        result['res_id'] = express_ids
        result['context'] = {'default_sale_id':order_id,'default_customer':partner_id,'default_picking_id':ids[0]}	
		
        return result		
	
	
class sale_order_line(osv.osv):
    _inherit = "sale.order.line"
	
    _columns = {
        'logistic_sent': fields.boolean(u'已同步运单?',default=False),	
        'coe_no': fields.many2one('sale.coe',string='COE NO'),	
        'tmi_jdi_no': fields.char(string='TM_JD NO'),
        'pay_time': fields.datetime('PayTime'),	
        'create_time_tmjd': fields.datetime('TM_JD Create Time'),		
    }	
	
    def copy_sale_order_line(self, cr, uid, ids, context=None): 
        for line in self.pool.get('sale.order.line').browse(cr, uid, ids, context=context):
            line.copy()	
			
class stock_move(osv.osv):
    _inherit = "stock.move"
	
    def _get_coe_no(self, cr, uid, ids, field_name, arg, context=None):	
        result = {}
        for move in self.pool.get('stock.move').browse(cr, uid, ids, context=context):
            result[move.id] = move.procurement_id.sale_line_id.coe_no.id
        return result	
		
    _columns = {
        #'sale_order_line': fields.function(_get_sale_order_line, type='char',string='Sales Line'),	
        'coe_no': fields.function(_get_coe_no,type='many2one',relation='sale.coe',string='COE NO'),
    }	