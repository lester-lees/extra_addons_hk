# -*- encoding: utf-8 -*-
from openerp.osv import fields,osv
import json
from jdapi.WaresListGetRequest import WaresListGetRequest
from jdapi.WaresListingGetRequest import WaresListingGetRequest
from jdapi.OrderSearchRequest import OrderSearchRequest
from datetime import datetime, timedelta
import logging
_logger = logging.getLogger(__name__)


class loewieec_jdshop(osv.osv):
    _inherit = 'loewieec.shop'
	
    def clean_jdi_orders(self, cr, uid, ids, orders, shop, context=None):
        statement = "select tmi_jdi_no from sale_order_line where tmi_jdi_no is not Null and state not in ('cancel','draft') group by tmi_jdi_no"
        cr.execute(statement)
        exist_tmijdi_no = []
        res = []	
        last_log = []
		
        for item in cr.fetchall():
        	exist_tmijdi_no.append(item[0])
      			
        for order in orders:            
            if str(order["order_id"]) not in exist_tmijdi_no and order.get('vender_remark').find('jaycee') >= 0:
                res.append(order)
            else:
                last_log.append( str(order["order_id"]) )
        if len(last_log) > 0:
            shop.last_log = u"以下电商单号ERP中已存在,所以此次未导入: " + chr(10) + ",".join(last_log) + chr(10)
        return res	
		
    def import_orders_from_jd(self, cr, uid, ids, context=None):	
        shop_id = self.browse(cr, uid, ids[0], context= context)
        req = OrderSearchRequest(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret)	
        req.optional_fields = 'order_id,order_source,order_total_price,order_payment,freight_price,order_state,vender_remark,order_start_time,consignee_info,item_info_list,payment_confirm_time,waybill,logistics_id,store_order,parent_order_id'
        req.page_size = 100	
        req.page = 1  	
        req.order_state = 'WAIT_SELLER_STOCK_OUT,WAIT_GOODS_RECEIVE_CONFIRM'
		
        req.end_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")	
        hours_interval = shop_id.sync_interval
        req.start_date = (datetime.now() - timedelta(hours=hours_interval)).strftime('%Y-%m-%d %H:%M:%S')		
		
        resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
        order_info_list = resp.get('order_search_response').get('order_search').get('order_info_list')
		
        orders = self.clean_jdi_orders(cr, uid, ids, order_info_list, shop_id, context=context)		
        self.create_order_for_jd(cr, uid, ids, orders, context=context)		
	
    def create_order_for_jd(self, cr, uid, ids, orders, context=None):	
        order_obj = self.pool.get('sale.order')
        shop = self.browse(cr, uid, ids[0], context = context)	
        partner_id = shop.partner_id.id		
        gift_product_id = shop.gift_product_id.id		
		
        order_val = {
            'name': "%s_%s" % ( shop.code, self.pool.get('ir.sequence').get(cr, uid, 'sale.order') or '/' ),
            'shop_id': shop.id,
            'date_order':  datetime.now(),      #订单支付时间 trade.get('pay_time') or 
            'create_date': datetime.now(),  #trade.get('created'),       #订单创建时间
            'partner_id': partner_id,
            'partner_invoice_id': partner_id, 			
            'partner_shipping_id': partner_id,
            'warehouse_id': shop.warehouse_id.id,
            'pricelist_id': shop.pricelist_id.id,
            'company_id': 1,			
            'all_discounts': 0,
            'picking_policy': 'one',
            'state':'draft',		
            'user_id': uid, 			
            'order_policy': 'picking',
            'client_order_ref': u'Loewieec_sync Generated',			
            'order_line': [],
        }	
		
        order_lines = []			
				
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
                    return osv.except_osv(u"Product Name Error",u'''Cann't Product:%s in ERP.''' % order_line.get('sku_name'))

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
			
        order_id = order_obj.create(cr, uid, order_val, context = context)		

        return order_id
	
    def get_jd_access_token(self, cr, uid, ids, context=None):
        shop_id = self.browse(cr, uid, ids[0], context= context)	
        url = 'https://oauth.jd.com/oauth/authorize?response_type=code&client_id=%s&redirect_uri=%s' % (shop_id.appkey, shop_id.authurl)	
        return {'type':'ir.actions.act_url', 'url':url, 'target':'new'}	
		
    def import_orders_from_jd_bk(self, cr, uid, ids, context=None):	
        shop_id = self.browse(cr, uid, ids[0], context= context)
        req = OrderSearchRequest(shop_id.apiurl, 443, shop_id.appkey, shop_id.appsecret)	
        req.fields = 'ware_id,skus,cid,brand_id,vender_id,shop_id,ware_status,title,item_num,upc_code,market_price,stock_num,status,weight,shop_categorys,property_alias'
        req.ware_ids = '1950500375,1954692765,1954700506,1954996897,1951075519'		
        resp= req.getResponse(shop_id.sessionkey or shop_id.access_token)
        total_results = resp.get('360buy_wares_list_get_response').get('wareListResponse').get('wares')	

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