# -*- encoding: utf-8 -*-
from openerp.osv import fields,osv
from openerp.tools.translate import _
import json
from jdapi.WaresListGetRequest import WaresListGetRequest
from jdapi.WaresListingGetRequest import WaresListingGetRequest
from jdapi.OrderSearchRequest import OrderSearchRequest
from jdapi.OverseasOrderSopDelivery import OverseasOrderSopDelivery
from jdapi.VenderAllDeliveryCompanyGet import VenderAllDeliveryCompanyGet
from jdapi.OrderGetRequest import OrderGetRequest
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)

							
class loewieec_jdshop(osv.osv):
    _inherit = 'loewieec.shop'
		
    _columns = {
        'sz_sale_id': fields.integer( string='SZ Sales ID',readonly=True,default=0),
        'sz_sale_order':fields.char(string=u'深圳ERP订单',readonly=True),		
    }	
		
    def jdi_order_delivery(self, cr, uid, ids, salesorder=None, context=None):
        if not salesorder : return False	
        shop_id = self.browse(cr, uid, ids[0], context= context)		
        req = OverseasOrderSopDelivery(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret) 
        express_ids = []
        log = []		
        
        for line in salesorder.order_line:
            coe_no = line.coe_no and line.coe_no.name or ''	
            tmi_jdi_no = line.tmi_jdi_no.strip()						
            if not tmi_jdi_no or not coe_no or (coe_no in express_ids) or line.logistic_sent : continue
			
            req.order_id = tmi_jdi_no
            req.logistics_id = 465 # JD EMS id no
            req.waybill = coe_no
            try:			
                resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
                line.coe_no.write({'logistic_sent':True, 'state':'done'})				
            except Exception, e:
                log.append(tmi_jdi_no)			
                _logger.info("Jimmy:%s" % str(e))				
            express_ids.append( tmi_jdi_no )	#  + '---' +  str(e)		
              	
        if log :
            note = salesorder.note or ''		
            salesorder.note = chr(10) + u'以下JD单未能成功上传运单(时间 %s):' % self.get_datetime_now_str() + chr(10) + ','.join(log)		
			
        return True
			
    def get_datetime_now_str(self):
        return (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')	
		
    def get_datetime_now(self):
        return datetime.now() + timedelta(hours=8)	
	
    def clean_jdi_orders(self, cr, uid, ids, orders, shop, context=None):
        statement = "select tmi_jdi_no from sale_order_line where tmi_jdi_no is not Null and state not in ('cancel','draft') group by tmi_jdi_no"
        cr.execute(statement)
        exist_tmijdi_no = []
        normal_list = []
        si_fang_list = []		
        last_log = []
        last_log_sz = []
        last_log_jaycee = []		
        last_log_sifang = []
		
        for item in cr.fetchall():
        	exist_tmijdi_no.append(item[0])

        for order in orders:  
	
            if str(order["order_id"]) in exist_tmijdi_no :		
                last_log.append( str(order["order_id"]) )
                order['is_duplicated'] = True				
                continue				
				
            remark = order.get('vender_remark')	
            if remark.strip() == '': continue
			
            if remark.find(u'香港四方转运') >= 0 :
                #si_fang_list.append(order)
                last_log_sifang.append( str(order["order_id"]) )				
                continue			
			
            if remark.find(u'jaycee订单') >= 0 or remark.find(u'anja订单') >= 0:
                last_log_jaycee.append( str(order["order_id"]) )				
                continue				

            if remark.find(u'深圳发货') >= 0:
                last_log_sz.append( str(order["order_id"]) )				
                continue			
				
            if remark.find(u'香港发货') >= 0 :
                normal_list.append(order)
				
        note = shop.last_log or ""	
        if len(last_log_sifang) > 0:
            note += 	u"香港四方转运订单：" + chr(10) + ",".join(last_log_sifang) + chr(10)		
        if len(last_log) > 0:
            note += 	u"重复订单：" + chr(10) + ",".join(last_log) + chr(10)
        if len(last_log_sz) > 0:			
            note += u"深圳订单：" + chr(10) + ",".join(last_log_sz) + chr(10)
        if len(last_log_jaycee) > 0:			
            note += u"Jaycee-anja订单：" + chr(10) + ",".join(last_log_jaycee) + chr(10)			
        shop.last_log =  self.get_datetime_now_str() + chr(9) + note
			
        return normal_list, si_fang_list	

    def search_jdi_orders_by_tids(self, cr, uid, ids, context=None, tids = ''):  # 根据电商单号 下载 订单
        port = 80
        shop = self.browse(cr, uid, ids[0], context = context)		
        req = OrderGetRequest(shop.apiurl,port, shop.appkey, shop.appsecret) 		
        req.optional_fields ="order_id,order_payment,order_state,vender_remark,consignee_info,item_info_list,order_start_time,payment_confirm_time,pin,waybill,logistics_id"
		
        tids = []
        note = shop.last_log or ''	
        tmijdi_nos = note.strip().split(',')     	
        for tmijdi_no in tmijdi_nos:
            tmijdi_no = tmijdi_no.strip()		
            if tmijdi_no != '' : tids.append( tmijdi_no )
			
        order_list = []		
        for tid in tids:            	
            req.order_id = tid
            resp = req.getResponse(shop.sessionkey) # orderDetailInfo
            order = resp.get('order_get_response').get('order', '').get('orderInfo', '')				
		
            if order : 	
                seller_memo = order.get('vender_remark')
                order['is_jaycee'] = seller_memo.find(u'jaycee订单') >= 0 or seller_memo.find(u'anja订单') >= 0		
                order['is_kevin'] = seller_memo.find(u'kevin订单') >= 0 or seller_memo.find(u'anja订单') >= 0	
                order['is_sz'] = seller_memo.find(u'深圳发货') >= 0				
                if not order['is_jaycee'] and not order['is_kevin'] : order['is_sz'] = True			
                order_list.append( order )	
				
        order_id = self.create_order_for_jd(cr, uid, ids, order_list, context = context )
        if order_id : shop.import_salesorder = order_id
        return order_id		
		
    def import_orders_from_jd(self, cr, uid, ids, context=None):	
        shop_id = self.browse(cr, uid, ids[0], context= context)
		
        req = OrderSearchRequest(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret)
        		
        req.optional_fields = 'order_id,order_payment,order_state,vender_remark,consignee_info,item_info_list,order_start_time,payment_confirm_time,pin,waybill,logistics_id'		
        req.page_size = 100	
        req.page = 1  	
        req.dateType = 1		
        #req.sortType = 1		
        req.order_state = 'WAIT_SELLER_STOCK_OUT,WAIT_SELLER_DELIVERY'		
		 				
        ctx_end_time = context.get('end_time',False)
        end_time = ctx_end_time and (datetime.strptime(ctx_end_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=8)) or self.get_datetime_now()
        end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S')		
        req.end_date = end_time_str
		
        hours_interval = shop_id.sync_interval  # shop
        # if not hours_interval : hours_interval = 24
		
        ctx_start_time = context.get('start_time',False)		
        start_time = ctx_start_time and ( datetime.strptime(ctx_start_time, '%Y-%m-%d %H:%M:%S') + timedelta(hours=8) )
        if hours_interval : start_time = start_time or ( end_time and (end_time - timedelta(hours=hours_interval)) ) or ( datetime.now() - timedelta(hours=hours_interval-8) )	
        start_time_str = start_time and start_time.strftime('%Y-%m-%d %H:%M:%S') 		
        if start_time_str : req.start_date = start_time_str	 		
		
        order_total = 1000
        total_get = 0		
        order_info_list = []		
        while total_get < order_total :		
            resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
            order_total = resp.get('order_search_response').get('order_search').get('order_total')            			
			
            if order_total > 0:
                order_info_list += resp.get('order_search_response').get('order_search').get('order_info_list')	
				
            total_get += req.page_size			
            req.page = req.page + 1				
		
        hk_list, si_fang_list = self.clean_jdi_orders(cr, uid, ids, order_info_list, shop_id, context=context)
		
        order_id = order_id2 = 0		
        if hk_list : order_id = self.create_order_for_jd(cr, uid, ids, hk_list, context=context)
		
        #if si_fang_list : order_id2 = self.create_order_for_jd( cr, uid, ids, si_fang_list, context=context.update({'is_si_fang':True}) )
		
        if order_id : #or order_id2 : 
            shop_id.write({'import_salesorder':order_id})
		
        return order_id		
			
    def create_order_for_jd(self, cr, uid, ids, orders, context=None):
        shop = self.browse(cr, uid, ids[0], context = context)
        order_obj = self.pool.get('sale.order')
        partner_id = shop.partner_id.id		
        gift_product_id = shop.gift_product_id and shop.gift_product_id.id or None	
        gift_qty = shop.gift_qty or 1	
		
        if not context: context = {}		
        client_order_ref = context.get('is_si_fang',False) and u'香港四方转运' or u'Loewieec_sync Generated'		
        order_val = {
            'name': "%s_%s" % ( shop.code, self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/' ),
            'shop_id': shop.id,
            'date_order':  datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,      # 订单支付时间 trade.get('pay_time') or 
            'create_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,  # trade.get('created'),       #订单创建时间
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
            'client_order_ref': client_order_ref,			
            'order_line': [],
        }	
		
        order_lines = []			
        note = shop.last_log or ""
        coe_obj = self.pool.get('sale.coe')	
        product_tmalljd_objs = self.pool.get('product.tmalljd')		
        for order in orders:
		
            order_jd_no = order.get('order_id')	
			
            			
            # is_qiju = False	            
            for oline in order['item_info_list']:	
                product_tmalljd_ids = product_tmalljd_objs.search(cr, uid, [('ec_sku_id','=',oline.get('sku_id') or oline.get('ware_id'))], context = context )
            
                #如果没有匹配到产品，报同步异常
                if not product_tmalljd_ids:
                    syncerr = "Below product doesn't exist in ERP: order_id=%s, ware_id=%s, sku_id=%s " % ( order_jd_no, oline.get('ware_id', ''),  oline.get('sku_id', '') )
                    self.pool.get('loewieec.error').create(cr, uid, {'name':syncerr, 'shop_id':shop.id }, context = context )
                    raise osv.except_osv(u"Product Name Error",u'''Cann't Product:%s in ERP.''' % oline.get('sku_name'))
					
                product_tmalljd_obj = product_tmalljd_objs.browse(cr, uid, product_tmalljd_ids[0], context = context)					
                #oline['product_id'] = product_tmalljd_obj.erp_product_id.id			
                product_id = product_tmalljd_obj.erp_product_id.id	
				
                """
                name_template = product_tmalljd_obj.erp_product_id.name_template
                if name_template.find("ml") < 1 :  # 如果发现产品不是液体则HK-ERP不导入此订单，默认由深圳SZ-ERP发货
                    is_qiju = True
                    break				
                oline['product_id'] = product_tmalljd_obj.erp_product_id.id	
            if is_qiju : continue	  # 如果存在器具，就不导入HK-ERP，而由SZ-ERP出货		
                """  			
            consignee = order.get('consignee_info')			
            fullname = consignee.get('fullname')
            province = consignee.get('province')
            city = consignee.get('city')
			
            vals = {			
                'name':fullname,
                'receive_name':fullname,	# receive_name			
                'mobile':consignee.get('mobile'),
                'telephone':consignee.get('telephone'),		
                'tmi_jdi_no':order_jd_no,	
                'county': consignee.get('county'),				
                'city': city,
                'province': province,				
                'address':consignee.get('full_address'), 
                'tel':consignee.get('telephone'),	 
            }	
            coeids = coe_obj.search(cr,uid,[('tmi_jdi_no','=',order_jd_no)],context=context)
            coeid = coeids and coeids[0] or 0			
            if not coeid :
			
                statement = "select postcode from sale_coe_postcode where position(province in '%s')>0 and position(city in '%s')>0 order by id asc limit 1" % (province,city) 
                cr.execute(statement)
                postcode = [o[0] for o in cr.fetchall()]				
                if postcode : vals['zip'] = postcode[0] 
                else: vals['zip'] = '100000' 	
				
                coeid = coe_obj.create( cr, uid, vals, context=context )        # 创建COE 条目，但 COE编号尚未获取  
           				
            #for order_line in order['item_info_list']:		
                line_vals = {			
                    'product_uos_qty': oline.get('item_total'),
                    'product_id': product_id,
                    'tmi_jdi_no': order_jd_no,
                    'coe_no': coeid,					
                    'pay_time':order.get('payment_confirm_time'),	
                    'create_time_tmjd':order.get('order_start_time'),
                    'buyer_nick':order.get('pin'),						
                    'product_uom': 1,
                    'price_unit': 1,
                    'product_uom_qty': oline.get('item_total'),
                    'name':'-',
                    'delay': 7,
                    'discount': 0,
                    'price_unit': float(oline.get('jd_price'))/int(oline.get('item_total')),					
                }		
                order_val['order_line'].append( (0, 0, line_vals) ) 
				
            if not gift_product_id : continue				
            gift_vals = {	  # 添加 赠品行		
                'product_uos_qty': gift_qty,
                'product_id': gift_product_id,
                'coe_no': coeid,				
                'tmi_jdi_no': order_jd_no,
                'pay_time':order.get('payment_confirm_time'),	
                'create_time_tmjd':order.get('order_start_time'),
                'buyer_nick':order.get('pin'),					
                'product_uom': 1,
                'price_unit': 0,
                'product_uom_qty': gift_qty,
                'name': '.',
                'delay': 7,
                'discount': 0,
            }	
            order_val['order_line'].append( (0, 0, gift_vals) )		
			
        if len(order_val['order_line']) < 1: 	
            shop.last_log = u'''时间:%s,JD 后台无有效订单''' % self.get_datetime_now_str() + chr(10) + note		
            return False					
			
        order_val['note'] = note			
        order_id = order_obj.create(cr, uid, order_val, context = context)			
        #shop.import_salesorder = order_id
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