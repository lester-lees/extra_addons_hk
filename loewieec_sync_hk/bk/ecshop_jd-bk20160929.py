# -*- encoding: utf-8 -*-
from openerp.osv import fields,osv
from openerp.tools.translate import _
import json
from jdapi.WaresListGetRequest import WaresListGetRequest
from jdapi.WaresListingGetRequest import WaresListingGetRequest
from jdapi.OrderSearchRequest import OrderSearchRequest
from datetime import datetime, timedelta
import xmlrpclib
import logging
_logger = logging.getLogger(__name__)

							
class loewieec_jdshop(osv.osv):
    _inherit = 'loewieec.shop'
	
    _db = "LoewieSZ"	
    _pwd = "Ufesbdr$%HG&hgf2432"
    _userid = 1	
    _peer_company = u'深圳市乐易保健用品有限公司'
    _company = 	u"深圳市乐易保健用品有限公司"
    _peer_url = "http://192.168.0.200:8069/xmlrpc/object"	
    _peer_redirect = 'http://192.168.0.200:8069/web?#id=%s&view_type=form&model=sale.order&menu_id=294&action=359'		

    _columns = {
        'sz_sale_id': fields.integer( string='SZ Sales ID',readonly=True,default=0),
        'sz_sale_order':fields.char(string=u'深圳ERP订单',readonly=True),		
    }	
	
    def query_id_byname(self, model, name):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, model, 'search', [('name','=',name)] )			
        if len(ids) == 0: return 0

        return ids[0]		
		
    def query_user_id_bylogin(self, login):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, 'res.users', 'search', [('login','=',login)] )			
        if len(ids) == 0: return 0

        return ids[0]		
		
		
    def query_partner(self, partner):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute( self._db, 1, self._pwd, 'res.partner', 'search', [('name','=',partner)] )	
        if len(ids) < 1: return 0,0	
		
        res = my_proxy.execute( self._db, 1, self._pwd, 'res.partner', 'read', ids[0], ['company_id'] )	        		
        if len(res) == 0: return 0,0

        return res['id'],res['company_id'][0]			

    def query_pricelist(self, pricelist):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute( self._db, 1, self._pwd, 'product.pricelist', 'search', [('name','=',pricelist)] )	     		
        if len(ids) == 0: return 0

        return ids[0]
	
    def query_product_id_by_name_template(self, model, name):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, model, 'search', [('name_template','=',name)] )			
        if len(ids) == 0: return 0

        return ids[0]

    def query_product_id_by_sku(self, sku):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, 'product.tmalljd', 'search', [('ec_sku_id','=',sku)] )			
        if len(ids) == 0: return 0
        res = my_proxy.execute(self._db, 1, self._pwd, 'product.tmalljd', 'read', ids[0], ['erp_product_id'] )
        if len(res) < 1: return 0,0		
        return res['erp_product_id'][0]		

    def query_product_id_by_ean13(self, model, ean13):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, model, 'search', ['|',('ean13','=',ean13),('default_code','=',ean13)] )			
        if len(ids) == 0: return 0

        return ids[0]

    def query_saleorderline_by_tmijdino(self, tmi_jdi_no):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, 'sale.order.line', 'search', [('tmi_jdi_no','=',tmi_jdi_no),('state','not in',['draft','cancel'])] )			
	
        return len(ids)			

    def create_sz_salesorder_tmi(self, cr, uid, ids, sz_orders, context=None):   
        shop = self.browse(cr, uid, ids[0], context = context)	
        model1 = "sale.order"			
        method = "create"		
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
		
        user_obj = self.pool.get('res.users').browse(cr,uid,[uid],context=context)
        remote_uid = self.query_user_id_bylogin(user_obj.login) or 1		
        partner_id,company_id = self.query_partner(u'TMI天猫国际')
        pricelist_id = self.query_pricelist('Wholesale_CNY')	
        if not partner_id or not pricelist_id : 
            raise osv.except_osv(_(u'Ecshop JD'),_(u'''在深圳ERP中无法找到合适的 价格表 与 partner！''') )		
            return False				
		
        order_val = {
            'date_order':  datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,      
            'create_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,  
            'partner_id': partner_id,
            'partner_invoice_id': partner_id, 			
            'partner_shipping_id': partner_id,
            'warehouse_id': 1,
            'pricelist_id': pricelist_id,  
            'company_id': 1,			
            'all_discounts': 0,
            'picking_policy': 'direct',
            'state':'draft',		
            'user_id': remote_uid,		
            'order_policy': 'picking',
            'client_order_ref': u'Loewieec from hk-erp',			
            'order_line': [],
        }	
		
        gift_product_id = self.query_product_id_by_name_template('product.product','Eros - Gift Sachet Set')
        null_product_id = self.query_product_id_by_name_template('product.product',u'刷单空包')			
        order_lines = []
        sz_dup_list = []		
        for order in sz_orders:		
            if not order['is_kevin'] and not order['is_sz'] : 	
                continue	
            tmi_order_no = str( order.get('tid') )				
            if self.query_saleorderline_by_tmijdino(tmi_order_no): 
                sz_dup_list.append(tmi_order_no)			
                continue				
            gift_vals = {	 				
                'product_uos_qty': 1,      # 正常订单添加赠品行, Jaycee订单则添加"刷单空包"
                'product_id': order['is_sz'] and gift_product_id or null_product_id,  	
                'tmi_jdi_no': str(order.get('tid')),			
                'product_uom': 1,
                'price_unit': 0,
                'product_uom_qty': 1,
                'name': '-',
                'delay': 7,
                'discount': 0,
            }				
            order_val['order_line'].append( (0, 0, gift_vals) ) 
			
            if 	order['is_kevin'] : continue   # 刷单订单，无需添加产品行，直接跳过
			
            lines = order["orders"]["order"]
            store_code = ''			
            for line in lines:
                store_code = line.get('store_code') or ''				
                if store_code in ['loewie','']	:	
                    line['description'] = "-"				
                    if store_code == '' : line['description'] = u'保税仓?'							
                    order_lines.append(line)					
					
        for order_line in order_lines: 	
            tid = str ( order_line.get('tid')	or order_line.get('oid') )	
            qty = order_line.get('num')	
            product_id = self.query_product_id_by_sku( order_line.get('sku_id') )
            price = float(order_line.get('payment',0))/qty or float(order_line.get('total_fee',0))/qty					
					
            if not product_id:
                raise osv.except_osv(u"Product Name Error",u'''Cann't Product:%s in SZ ERP.''' % order_line.get('sku_name'))
				
            line_vals = {			
                'product_uos_qty': qty,
                'product_id': product_id,
                'tmi_jdi_no': tid,			
                'product_uom': 1,
                'price_unit': price,
                'product_uom_qty': qty,
                'name':'-',
                'delay': 7,
                'discount': 0,
            }							
            order_val['order_line'].append( (0, 0, line_vals) ) 

			
        if len(order_val['order_line']) < 1: 
            tmp_log = shop.last_log or ''
            shop.last_log = self.get_datetime_now() + ' - No Sz order!' + chr(10) + tmp_log			
            return True
		
        value = my_proxy.execute(self._db, 1, self._pwd, model1, method, order_val )
        if not value:
            raise osv.except_osv(_(u'Ecshop JD'),_(u'''未能创建深圳ERP订单''') )		
            return False            		
			
        if len(sz_dup_list) > 0: 
            tmp_log = shop.last_log or ''			
            tmp_log = ",".join(sz_dup_list)  + chr(10) + tmp_log			
            shop.last_log =  self.get_datetime_now() + u'以下SZ-ERP中已有以下JD订单:' + tmp_log	
			
        order_name = my_proxy.execute(self._db, 1, self._pwd, model1, 'read', value, ['name'] )			
        shop.sz_sale_id = value
        shop.sz_sale_order = order_name['name']		
        return value		
		
    def view_sz_sales_order(self, cr, uid, ids, context=None):
        shop = self.browse(cr, uid, ids[0], context = context)		
        if not shop.sz_sale_id	: return False 
		
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        remote_id = my_proxy.execute(self._db, 1, self._pwd, 'sale.order', 'search', [('id','=',shop.sz_sale_id)] )
        if not remote_id: 
            #shop.sz_sale_id = 0
            order_name = shop.sz_sale_order			
            #shop.sz_sale_order = ''
            raise osv.except_osv(_(u'Ecshop JD'),_(u'''在深圳ERP中无法找到销售订单:%s !!!''' % order_name) )			
            return False		
		
        return {'type':'ir.actions.act_url', 'url':self._peer_redirect % shop.sz_sale_id, 'target':'new'}		
 
    def get_datetime_now(self):
        return (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')	
    
    def create_sz_erp_salesorder(self, cr, uid, ids, sz_orders, context=None):   
        shop = self.browse(cr, uid, ids[0], context = context)	
        model1 = "sale.order"			
        method = "create"		
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
		
        user_obj = self.pool.get('res.users').browse(cr,uid,[uid],context=context)
        remote_uid = self.query_user_id_bylogin(user_obj.login) or 1		
        partner_id,company_id = self.query_partner(u'JDI京东国际')
        pricelist_id = self.query_pricelist('Wholesale_CNY')	
        if not partner_id or not pricelist_id : 
            raise osv.except_osv(_(u'Ecshop JD'),_(u'''在深圳ERP中无法找到合适的 价格表 与 partner！''') )		
            return False				
		
        order_val = {
            'date_order':  datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,      
            'create_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,  
            'partner_id': partner_id,
            'partner_invoice_id': partner_id, 			
            'partner_shipping_id': partner_id,
            'warehouse_id': 1,
            'pricelist_id': pricelist_id,  
            'company_id': 1,			
            'all_discounts': 0,
            'picking_policy': 'direct',
            'state':'draft',		
            'user_id': remote_uid,		
            'order_policy': 'picking',
            'client_order_ref': u'Loewieec from hk-erp',			
            'order_line': [],
        }	
		
        gift_product_id = self.query_product_id_by_name_template('product.product','Eros - Gift Sachet Set')
        null_product_id = self.query_product_id_by_name_template('product.product',u'刷单空包')		
        express = {}
        sz_dup_list = []		
        for order in sz_orders:
            vender_remark = order.get('vender_remark')		
            is_jaycee_order = vender_remark.find(u'jaycee订单')>=0
            consignee = order.get('consignee_info')		
            address = "%s %s %s" % (consignee.get('province'),consignee.get('city'),consignee.get('full_address'))	
            order_id = order.get('order_id')

            if self.query_saleorderline_by_tmijdino(order_id): 
                sz_dup_list.append(order_id)			
                continue
			
            vals = {	# 为每个收件人 在深圳ERP中创建COE 条目 		
                #'sale_id': consignee.get(''),			
                'name':consignee.get('fullname'),
                'mobile':consignee.get('mobile'),
                'tmi_jdi_no':order_id,			
                'address':address,  # consignee.get('full_address'), 
                #'city':consignee.get('city'), 
                #'state':consignee.get('province'),
                'tel':consignee.get('telephone'),
                'pay_way':'cash_pay',	
                'expresser': 1,				
                #'zip':consignee.get(''), 
            }
            express_id = my_proxy.execute(self._db, 1, self._pwd, 'sale.coe', 'search', [('name','=',vals["name"]),('mobile','=',vals['mobile']),('tmi_jdi_no','=',order_id)] )   #先查找是否已经创建
            express_id = express_id and express_id[0] or 0			
            if not express_id :			
                express_id = my_proxy.execute(self._db, 1, self._pwd, 'sale.coe', 'create', vals)	
            vals["id"] = express_id	           	
            express[vals["mobile"]]	= vals	
	          				
            gift_vals = {	 	
                'express_id':express_id,			
                'product_uos_qty': 1,
                'product_id': is_jaycee_order and null_product_id or gift_product_id,
                'tmi_jdi_no': order.get('order_id'),			
                'product_uom': 1,
                'price_unit': 0,
                'product_uom_qty': 1,
                'name': '-',
                'delay': 7,
                'discount': 0,
            }				
            order_val['order_line'].append( (0, 0, gift_vals) ) 			
			
            if is_jaycee_order : continue       # 非刷单(jaycee订单) 则需添加 赠品行
			
            for order_line in order['item_info_list']:	
                qty = int(order_line.get('item_total'))		
                product_id = self.query_product_id_by_sku( order_line.get('sku_id') )					
                if not product_id:
                    raise osv.except_osv(u"Product Name Error",u'''No Product:%s in SZ ERP.''' % order_line.get('sku_name')	)				
                jd_price = float( order_line.get('jd_price') ) / qty
                line_vals = {	
                    'express_id':express_id,				
                    'product_uos_qty': qty,
                    'product_id': product_id,
                    'tmi_jdi_no': order.get('order_id'),			
                    'product_uom': 1,
                    'product_uom_qty': qty,
                    'name':'-',
                    'delay': 7,
                    'discount': 0,
                    'price_unit': jd_price,					
                }			
                order_val['order_line'].append( (0, 0, line_vals) ) 				
	
        if len(order_val['order_line']) < 1: 
            tmp_log = shop.last_log or ''
            shop.last_log =  self.get_datetime_now() + ' No Sz order!' + chr(10) + tmp_log			
            return True
			
        if len(sz_dup_list) > 0: 
            tmp_log = shop.last_log or ''			
            tmp_log = ",".join(sz_dup_list)  + chr(10) + tmp_log			
            shop.last_log =  self.get_datetime_now() + u'以下SZ-ERP中已有以下JD订单:' + tmp_log					
		
        value = my_proxy.execute(self._db, 1, self._pwd, model1, method, order_val )
        if not value:
            raise osv.except_osv(_(u'Ecshop JD'),_(u'''未能创建深圳ERP订单''') )		
            return False            		
		
        for key in express.keys():    # 更新 express - sale.coe 的 sale_id 值
            express_id = express[key]['id']		
            my_proxy.execute(self._db, 1, self._pwd, 'sale.coe','write',express_id,{'sale_id':value,'expresser':3,'price':5} )
			
        order_name = my_proxy.execute(self._db, 1, self._pwd, model1, 'read', value, ['name'] )			
        shop.sz_sale_id = value
        shop.sz_sale_order = order_name['name']		
        return value		
	
    def clean_jdi_orders(self, cr, uid, ids, orders, shop, context=None):
        statement = "select tmi_jdi_no from sale_order_line where tmi_jdi_no is not Null and state not in ('cancel','draft') group by tmi_jdi_no"
        cr.execute(statement)
        exist_tmijdi_no = []
        hk_list = []
        jaycee_list = []
        sz_list = []		
        last_log = []
        last_log_sz = []
        last_log_jaycee = []		
		
        for item in cr.fetchall():
        	exist_tmijdi_no.append(item[0])

        for order in orders:  
            if str(order["order_id"]) in exist_tmijdi_no :		
                last_log.append( str(order["order_id"]) )
                orders['is_duplicated'] = True				
                continue				
				
            remark = order.get('vender_remark')		
            if remark.find('jaycee') >= 0:
                jaycee_list.append(order)
                last_log_jaycee.append( str(order["order_id"]) )				
                continue				

            if remark.find(u'深圳发货') >= 0:
                sz_list.append(order)
                last_log_sz.append( str(order["order_id"]) )				
                continue						

            hk_list.append(order)
				
        note = shop.last_log or ""		
        if len(last_log) > 0:
            note += 	u"重复订单：" + chr(10) + ",".join(last_log) + chr(10)
        if len(last_log_sz) > 0:			
            note += u"深圳订单：" + chr(10) + ",".join(last_log_sz) + chr(10)
        if len(last_log_jaycee) > 0:			
            note += u"Jaycee订单：" + chr(10) + ",".join(last_log_jaycee) + chr(10)			
        shop.last_log =  self.get_datetime_now() + chr(9) + note
			
        return hk_list, jaycee_list, sz_list	
		
    def import_orders_from_jd(self, cr, uid, ids, context=None):	
        shop_id = self.browse(cr, uid, ids[0], context= context)
		
        req = OrderSearchRequest(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret)
        		
        req.optional_fields = 'order_id,order_payment,order_state,vender_remark,consignee_info,item_info_list,payment_confirm_time,waybill,logistics_id'
		
        req.page_size = 20	
        req.page = 1  	
        req.dateType = 1		
        req.sortType = 1		
        req.order_state = 'WAIT_SELLER_STOCK_OUT,WAIT_SELLER_DELIVERY'	

        ctx_start_time = context.get('start_time',False)		
        ctx_start_time = ctx_start_time and ( datetime.strptime(ctx_start_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=8) ) 		
		
        ctx_end_time = context.get('end_time',False)	# datetime.strptime(string, "%Y-%m-%d-%H")
        ctx_end_time = ctx_end_time and datetime.strptime(ctx_end_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=8) 
        req.end_date = ctx_end_time and ctx_end_time.strftime('%Y-%m-%d %H:%M:%S') or self.get_datetime_now()	
		
        hours_interval = shop_id.sync_interval
        if not hours_interval : hours_interval = 24
		
        req.start_date = ctx_start_time or (ctx_end_time and (ctx_end_time - timedelta(hours=hours_interval)).strftime('%Y-%m-%d %H:%M:%S') ) or (datetime.now() - timedelta(hours=hours_interval-8)).strftime('%Y-%m-%d %H:%M:%S')			
		
        order_total = 100
        total_get = 0		
        order_info_list = []		
        while total_get < order_total :		
            resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
            order_total = resp.get('order_search_response').get('order_search').get('order_total')            			
			
            if order_total > 0:
                order_info_list += resp.get('order_search_response').get('order_search').get('order_info_list')	
				
            total_get += req.page_size			
            req.page = req.page + 1				
		
        hk_list, jaycee_list, sz_list = self.clean_jdi_orders(cr, uid, ids, order_info_list, shop_id, context=context)
        self.create_order_for_jd(cr, uid, ids, hk_list, context=context)		
        self.create_sz_erp_salesorder(cr, uid, ids, jaycee_list + sz_list, context=context)		
	
    def create_order_for_jd(self, cr, uid, ids, orders, context=None):
        shop = self.browse(cr, uid, ids[0], context = context)
        order_obj = self.pool.get('sale.order')
        partner_id = shop.partner_id.id		
        gift_product_id = shop.gift_product_id.id		
		
        order_val = {
            'name': "%s_%s" % ( shop.code, self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/' ),
            'shop_id': shop.id,
            'date_order':  datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,      #订单支付时间 trade.get('pay_time') or 
            'create_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,  #trade.get('created'),       #订单创建时间
            'partner_id': partner_id,
            'partner_invoice_id': partner_id, 			
            'partner_shipping_id': partner_id,
            'warehouse_id': shop.warehouse_id.id,
            'pricelist_id': shop.pricelist_id.id,
            'company_id': 1,			
            'all_discounts': 0,
            'picking_policy': 'direct',
            'state':'draft',		
            'user_id': uid, 			
            'order_policy': 'picking',
            'client_order_ref': u'Loewieec_sync Generated',			
            'order_line': [],
        }	
		
        order_lines = []			
        note = shop.last_log or ""				
        for order in orders:
		
            for order_line in order['item_info_list']:		
                line_vals = {			
                    'product_uos_qty': order_line.get('item_total'),
                    'product_id': 1,
                    'tmi_jdi_no': order.get('order_id'),			
                    'product_uom': 1,
                    'price_unit': 1,
                    'product_uom_qty': order_line.get('item_total'),
                    'name':'-',
                    'delay': 7,
                    'discount': 0,
                    'price_unit': float(order_line.get('jd_price'))/int(order_line.get('item_total')),					
                }			
                product_tmalljd_ids = self.pool.get('product.tmalljd').search(cr, uid, [('ec_sku_id','=',order_line.get('sku_id') or order_line.get('ware_id'))], context = context )
            
                #如果没有匹配到产品，报同步异常  coe_lines
                if not product_tmalljd_ids:
                    syncerr = "Below product doesn't exist in ERP: order_id=%s, ware_id=%s, sku_id=%s " % ( order.get('order_id'), order_line.get('ware_id', ''),  order_line.get('sku_id', '') )
                    self.pool.get('loewieec.error').create(cr, uid, {'name':syncerr, 'shop_id':shop.id }, context = context )
                    raise osv.except_osv(u"Product Name Error",u'''Cann't Product:%s in ERP.''' % order_line.get('sku_name'))

                product_tmalljd_obj = self.pool.get('product.tmalljd').browse(cr, uid, product_tmalljd_ids[0], context = context)
                product_id = product_tmalljd_obj.erp_product_id.id
                uom_id = product_tmalljd_obj.erp_product_id.uom_id.id			
	
                line_vals.update({'product_id': product_id  } )
                order_val['order_line'].append( (0, 0, line_vals) ) 

            gift_vals = {	  # 添加 赠品行		
                'product_uos_qty': 1,
                'product_id': gift_product_id,
                'tmi_jdi_no': order.get('order_id'),			
                'product_uom': 1,
                'price_unit': 0,
                'product_uom_qty': 1,
                'name': '.',
                'delay': 7,
                'discount': 0,
            }		
		
            order_val['order_line'].append( (0, 0, gift_vals) )	
            #consignee = order.get('consignee_info')			
            #consignee_info = "Order:%s, Receiver:%s, Phone:%s, Mobile:%s, State:%s, City:%s, Address:%s ;" % (order.get('order_id'),consignee.get('fullname'),consignee.get('telephone'),consignee.get('mobile'),consignee.get('province'),consignee.get('city'),consignee.get('full_address'))			
            #note += consignee_info + chr(10)	
			
        if len(order_val['order_line']) < 1: 	
            shop.last_log = u'''时间:%s,JD 后台有效订单已全部导入，或修改订单时段后再导.''' % self.get_datetime_now() + chr(10) + note		
            return True		
            #raise osv.except_osv(u'JD后台无有效订单',u'''JD 后台有效订单已全部导入，或修改订单时段后再导.''')			
			
        order_val['note'] = note			
        order_id = order_obj.create(cr, uid, order_val, context = context)			
        shop.import_salesorder = order_id
        return order_id
	
    def get_jd_access_token(self, cr, uid, ids, context=None):
        shop_id = self.browse(cr, uid, ids[0], context= context)	
        url = 'https://oauth.jd.com/oauth/authorize?response_type=code&client_id=%s&redirect_uri=%s' % (shop_id.appkey, shop_id.authurl)	
        return {'type':'ir.actions.act_url', 'url':url, 'target':'new'}	
		
    def search_jd_wares(self, cr, uid, ids, context=None):		
        shop_id = self.browse(cr, uid, ids[0], context= context)
        product_tmalljd_objs = self.pool.get('product.tmalljd')
			
        req = WaresListGetRequest(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret)	
        req.fields = 'ware_id,skus,cid,brand_id,vender_id,shop_id,ware_status,title,item_num,upc_code,market_price,stock_num,status,weight,shop_categorys,property_alias'
		
        ware_list = self.get_all_ware_ids(cr, uid, ids, context=context)
        if len(ware_list) < 1: return 
        ware_id_list = [str(o['ware_id']) for o in ware_list]  
        ware_info_list = []		
	
        interval = 10
        start = end = 0
        final_end = len(ware_id_list)
		
        while start < final_end:
            if start + interval > final_end	: end = final_end
            else: end = start + interval	
            sub_list = ware_id_list[start:end]			
            sub_num_iids = ",".join(sub_list)			           			
            start = end	
        		
            req.ware_ids = sub_num_iids		
            resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
            wares = resp.get('ware_list_response').get('wares')			
            if len(wares)>0 :ware_info_list +=  wares    

        for ware in ware_info_list :
	
            product_vals = {'ec_shop_id':shop_id.id,'ec_num_iid':str(ware['ware_id']), 'ec_title':ware["title"], 'ec_outer_code':ware.get('item_num') }		
            
            for sku_item in ware['skus'] :			
                pids = product_tmalljd_objs.search( cr, uid, [('ec_sku_id', '=', str(sku_item.get('sku_id'))),('ec_shop_id','=',shop_id.id)], context=context)		
                if len(pids) > 0: continue
                product_vals.update({'ec_sku_id': str(sku_item.get('sku_id')),'ec_price':float(sku_item.get('market_price')),'ec_qty':sku_item.get('stock_num'), 'ec_color':sku_item.get('color_value')})				
                product_tmalljd_objs.create(cr, uid, product_vals)		
	
    def get_all_ware_ids(self, cr, uid, ids, context=None):	
        shop_id = self.browse(cr, uid, ids[0], context= context)
        req = WaresListingGetRequest(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret)
        req.page_size = 100	
        req.page = 1		
        cids = ['1502','1504','1505','12610','12609']		
        req.fields = 'ware_id,cid'
        ware_list = []		
        for cid in cids :		
            req.cid = cid		
            resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
            ware_infos = resp.get('ware_listing_get_response')
            ware_infos = ware_infos.get('ware_infos')			
            if len(ware_infos)>0 :  ware_list += ware_infos
			
        return ware_list			