# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from datetime import datetime, timedelta
import xmlrpclib
from openerp.tools.translate import _

class xmlrpc_loewie(object):
    _db = "LoewieSZ"	
    _pwd = "Ufesbdr$%HG&hgf2432"
    _userid = 1	
    _peer_company = u"Loewie香港有限公司"
    _company = 	u"深圳市乐易保健用品有限公司"
	
    _peer_url = "http://192.168.0.200:8069/xmlrpc/object"	
    _peer_redirect = 'http://192.168.0.200:8069/web#id=%d&view_type=form&model=stock.picking&action=162&active_id=%d'	
    _peer_sale_redirect = 'http://192.168.0.200:8069/web#view_type=form&model=sale.order&menu_id=293&action=%d'
    _peer_purchase_redirect = 'http://192.168.0.200:8069/web#view_type=form&model=purchase.order&menu_id=323&action=%d'	

    def query_user_id_bylogin(self, login):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, 'res.users', 'search', [('login','=',login)] )			
        if len(ids) == 0: return 0

        return ids[0]
	
    def query_id_byname(self, model, name):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, model, 'search', [('name','=',name)] )			
        if len(ids) == 0: return 0

        return ids[0]		
	
    def query_id_by_field_val(self, model, field, val):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, model, 'search', [(field,'=',val)] )			
        if len(ids) == 0: return 0

        return ids[0]
		
    def query_product_id_by_name_template(self, name):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, 'product.product', 'search', [('name_template','=',name)] )			
        if len(ids) == 0: return 0

        return ids[0]

    def query_product_id_by_ean13(self, model, ean13):
        my_proxy = xmlrpclib.ServerProxy(self._peer_url)	
        ids = my_proxy.execute(self._db, 1, self._pwd, model, 'search', ['|',('ean13','=',ean13),('default_code','=',ean13)] )			
        if len(ids) == 0: return 0

        return ids[0]
		
    def get_datetime_now(self):
        return (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')
		

class loewie_purchase_order(osv.osv):
    _inherit = "purchase.order"

    _columns = {
        'remote_picking_id': fields.integer( string='SZ PickNO'),
        'picking_no':fields.char(string='PickNO'),	
        'remote_sale_id': fields.integer( string='Remote Sale ID', readonly=True),
        'remote_sale_no':fields.char(string=u'深圳ERP销售单', readonly=True),		
    }	

    def generate_remote_erp_sale(self, cr, uid, ids, context=None):	
        model = 'sale.order'	
        method = "create"		
        xml_obj = xmlrpc_loewie()	
        purchase_order = self.pool.get('purchase.order').browse(cr, uid, ids[0], context=context)
        my_proxy = xmlrpclib.ServerProxy(xml_obj._peer_url)

        remote_id = 0			
        if purchase_order.remote_sale_id:			
            remote_id = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model, 'search', [('id','=',purchase_order.remote_sale_id)] )			
        if remote_id :
            raise osv.except_osv(_(u'远端ERP销售单 已存在'),_(u'''请先删除远端ERP已生成的销售单：%s！！！''' % purchase_order.remote_sale_no))	
			
        user = self.pool.get('res.users').browse(cr,uid,uid,context=context)			
        user_id = xml_obj.query_id_by_field_val('res.users', 'login', user.login)
        partner_id = xml_obj.query_id_byname('res.partner',u'Loewie香港有限公司') # 502	
        if not partner_id : 
            raise osv.except_osv(_(u'错误'),_(u'''远端ERP不存在 Parnter:深圳市乐易保健用品有限公司！！！'''))
            return False			
			
        order_val = {
            'date_order':  datetime.now().strftime('%Y-%m-%d %H:%M:%S')	,       
            'create_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')	, 
            'partner_id': partner_id,
            'partner_invoice_id': partner_id, 			
            'partner_shipping_id': partner_id,
            'warehouse_id': 1,
            'pricelist_id': 42,
            'company_id': 1,			
            'all_discounts': 0,
            'picking_policy': 'direct',
            'state':'draft',		
            'user_id': user_id, 
            'create_uid': user_id,			
            'order_policy': 'picking',
            'client_order_ref': u'From Remote:%s' % purchase_order.name,			
            'order_line': [],
        }

        product_name_loss = []		
        for order_line in purchase_order.order_line: 	
		
            product_name = order_line.product_id.name_template		
            product_id = xml_obj.query_product_id_by_name_template( product_name )							
            if not product_id:
                product_name_loss.append(product_name)			
                continue # raise osv.except_osv(u"Product Name Error",u'''Cann't Product:%s in Remote ERP.''' % product_name)
				
            line_vals = {			
                'product_uos_qty': order_line.product_qty,
                'product_id': product_id,		
                'product_uom': 1,
                'price_unit': order_line.price_unit,
                'product_uom_qty': order_line.product_qty,
                'name':'-',
                'delay': 7,
                'discount': 0,
            }							
            order_val['order_line'].append( (0, 0, line_vals) )
        			
        note = purchase_order.notes or ''					
        if len(order_val['order_line']) < 1: 
            note = u'时间：' + xml_obj.get_datetime_now() + '所有产品 在远端系统中没有对应名称!' + chr(10) + note	
            purchase_order.write({'notes':note})			
            return True
						
        if product_name_loss :
            product_list = ','.join(product_name_loss)		
            order_val.update({ 'note': u'以下远端产品 在本地没有对应的产品名：' + product_list})		
            note = u'时间：' + xml_obj.get_datetime_now() + u', 远端ERP中 没有找到以下产品 ：' + chr(10) + product_list + chr(10) + note
			
        value = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model, method, order_val )
        if not value:
            raise osv.except_osv(_(u'Loewie Sync.'),_(u'''cann't create sales order in remote system.''') )		            		

        order_name = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model, 'read', value, ['name'] )[0]['name']
        res = {'remote_sale_id':value, 'remote_sale_no':order_name}	
        if product_name_loss: 		
		    res.update({'notes':note})
			
        purchase_order.write(res)	
				
        return True			

    def view_remote_erp_sale(self, cr, uid, ids, context=None):
        xml_obj = xmlrpc_loewie()	
        for po in self.browse(cr, uid, ids, context=context):
            if po.remote_sale_id > 0 :	 
                return {'type':'ir.actions.act_url', 'url':xml_obj._peer_sale_redirect % (po.remote_sale_id ), 'target':'new'}
	
	
    def action_picking_create(self, cr, uid, ids, context=None):
        xml_obj = xmlrpc_loewie()	
        user = self.pool.get('res.users').browse(cr,uid,uid,context=context)			
        remote_uid = xml_obj.query_id_by_field_val('res.users', 'login', user.login)
		
        vals_move = {	
            'create_uid':remote_uid, 		
            'product_id': 0, #, 
            'product_uom_qty':0, 
            'location_dest_id':xml_obj.query_id_byname('stock.location', u'成品'), 
            'location_id':xml_obj.query_id_byname('stock.location', 'Suppliers'), 
            'company_id': 1, 
            'date':datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'date_expected':(datetime.now() + timedelta(3)).strftime("%Y-%m-%d %H:%M:%S"), 
            'invoice_state':'none', 
            'name':'-', 
            'procure_method':'make_to_stock', 
            'state':'draft',			
            'product_uom':1, 
            'weight_uom_id':1,
            'picking_id': 0,			
        }		
		
        vals_pick = {
            'create_uid':remote_uid, 		
            'company_id': 1,
            'partner_id': xml_obj.query_id_byname('res.partner',u'Loewie香港有限公司'), 	
            'create_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),			
            'origin': 'HK-PO : %s',			
            #'invoice_state': 'none',			
            'move_type': 'direct',
            'picking_type_id': xml_obj.query_id_byname('stock.picking.type', u'Receipts(收货)'),			
            #'priority': 1,		
            #'weight_uom_id': 3,            			
        }		
	
        model1 = "stock.picking"		
        model2 = "stock.move"		
        method = "create" 		
	
        for order in self.browse(cr, uid, ids):
	
            if order.dest_address_id.name == xml_obj._company :		
                my_proxy = xmlrpclib.ServerProxy(xml_obj._peer_url)		

                if order.remote_picking_id :
                    remote_id = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model1, 'search', [('id','=',order.remote_picking_id)] )				
                    if remote_id: raise osv.except_osv(_(u'您已生成过 远端ERP入库单'),_(u'''请先删除远端ERP已生成的入库单：%s！''' % order.picking_no))
				
                vals_pick.update({'origin': 'HK-PO:%s' % order.name})				
                value = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model1,method, vals_pick )
                order.remote_picking_id = value		
                order.picking_no = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model1, 'read', [value], ['name'] )[0]['name']
                un_created_products = []				
                for line in order.order_line:
				
                    if line.product_id.type != 'product': continue
					
                    pid = xml_obj.query_product_id_by_name_template(line.product_id.name_template)
					
                    if not pid:
                        if not line.product_id.ean13 and not line.product_id.default_code :  pid=0					
                        else: pid = xml_obj.query_product_id_by_ean13('product.product', line.product_id.ean13 or line.product_id.default_code)
			
                    if pid > 0 :	
                        vals_move.update({'product_id':pid, 'product_uom_qty':line.product_qty, 'name': line.name, 'picking_id':value })	
                        my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model2, method, vals_move )						
                    else:
                        un_created_products.append(line.product_id.name_template)
						
                if len(un_created_products) > 0:
                    names = ""				
                    for name in un_created_products:    # note
                        names += name + " , " 					
                    order.notes = ( order.notes or "" ) + (u"   在远端ERP单据:%s 中无法找到与以下名字相同的产品：%s"  % (order.picking_no, names))
					
                    my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model1, 'write', value, {'notes': u"远端ERP单据:%s 中的以下产品名 没有在本地ERP中创建: %s" % (order.name, names)} )	
						
                continue				                
				
            picking_vals = {
                'picking_type_id': order.picking_type_id.id,
                'partner_id': order.dest_address_id.id or order.partner_id.id,
                'date': max([l.date_planned for l in order.order_line]),
                'origin': order.name
            }
            picking_id = self.pool.get('stock.picking').create(cr, uid, picking_vals, context=context)
            self._create_stock_moves(cr, uid, order, order.order_line, picking_id, context=context)
						
    def view_picking(self, cr, uid, ids, context=None):

        if context is None:
            context = {}
        mod_obj = self.pool.get('ir.model.data')
        dummy, action_id = tuple(mod_obj.get_object_reference(cr, uid, 'stock', 'action_picking_tree'))
        action = self.pool.get('ir.actions.act_window').read(cr, uid, action_id, context=context)

        xml_obj = xmlrpc_loewie()		
        pick_ids = []
        for po in self.browse(cr, uid, ids, context=context):
            if po.dest_address_id.name == xml_obj._company and po.remote_picking_id > 0 :	 
                return {'type':'ir.actions.act_url', 'url':'http://192.168.0.200:8069/web#id=%d&view_type=form&model=stock.picking&action=162&active_id=1' % po.remote_picking_id, 'target':'new'}	
				
            pick_ids += [picking.id for picking in po.picking_ids]

        #override the context to get rid of the default filtering on picking type
        action['context'] = {}
        #choose the view_mode accordingly
        if len(pick_ids) > 1:
            action['domain'] = "[('id','in',[" + ','.join(map(str, pick_ids)) + "])]"
        else:
            res = mod_obj.get_object_reference(cr, uid, 'stock', 'view_picking_form')
            action['views'] = [(res and res[1] or False, 'form')]
            action['res_id'] = pick_ids and pick_ids[0] or False
        return action			
    """	
    """
		
class sale_order(osv.osv):
    _inherit = "sale.order"
	
    _columns = {
        'remote_purchase_id': fields.integer( string='Remote Purchase ID', readonly=True),
        'remote_purchase_no':fields.char(string=u'深圳ERP采购单', readonly=True),		
    }		
	
    def generate_remote_erp_purchase(self, cr, uid, ids, context=None):	
        model = 'purchase.order'	
        method = "create"		
        xml_obj = xmlrpc_loewie()	
        sale_order = self.pool.get('sale.order').browse(cr, uid, ids[0], context=context)
        my_proxy = xmlrpclib.ServerProxy(xml_obj._peer_url)

        remote_id = 0			
        if sale_order.remote_purchase_id:			
            remote_id = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model, 'search', [('id','=',sale_order.remote_purchase_id)] )			
        if remote_id :
            raise osv.except_osv(_(u'远端ERP采购单 已存在'),_(u'''请先删除远端ERP已生成的采购单：%s！！！''' % sale_order.remote_purchase_no))
			
        user = self.pool.get('res.users').browse(cr,uid,uid,context=context)			
        user_id = xml_obj.query_id_by_field_val('res.users', 'login', user.login)	
        partner_id = xml_obj.query_id_byname('res.partner',u'Loewie香港有限公司') # 502	
        if not partner_id : 
            raise osv.except_osv(_(u'错误'),_(u'''远端ERP不存在 Parnter:深圳市乐易保健用品有限公司！！！'''))
            return False
			
        vals = {
            'create_uid': user_id,		
            'company_id': 1,
            'currency_id': 176,  # 176 USD ,, 8 CNY,, 175 HKD
            'date_order': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'location_id': 12, #  12 成品， 9,  
            # 'picking_type_id': 1,
            'partner_id': partner_id,
            # 'journal_id': 35,
            'pricelist_id': 43,
            # 'related_location_id': 12,
            'order_line': [],
            'remote_sale_no':sale_order.name,
            'remote_sale_id':ids[0],	
            'partner_ref': 'From remote:%s' % sale_order.name,			
        }      
  		
        products_remote_loss = []
        for line in sale_order.order_line:
            product_name = line.product_id.name_template               		
            product_id = xml_obj.query_product_id_by_name_template(product_name)
            if not product_id : 
                products_remote_loss.append(product_name)
                continue
				
            order_line = {
                'create_uid': user_id,				
                'name': line.name,
                'product_id': product_id,
                'product_qty': line.product_uom_qty,					
                'product_uom': 1, # line.product_uom.id,
                'date_planned': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'price_unit': line.price_unit,
                'pur_price_unit': line.price_unit,					
                #'taxes_id': [[6, False, [x.id for x in line.tax_id]]],
                'state': 'draft',
                # 'account_analytic_id': x
                # 'pur_currency_id': 3,   
            }
            vals['order_line'].append( (0,False,order_line) )
        if products_remote_loss :
            vals.update({'notes': u"远端ERP单据:%s 中的以下产品名 没有在本地ERP中创建: %s" % (sale_order.name, ','.join(products_remote_loss))})			
        value = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model, 'create', vals )
		
        remote_purchase_no = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model, 'read', [value], ['name'] )[0]['name']
        res = {'remote_purchase_id':value, 'remote_purchase_no':remote_purchase_no}					
        if products_remote_loss :
            note = sale_order.note or ''			
            note = u"远端ERP没有以下产品资料：" + ','.join(products_remote_loss) + chr(10) + note			
            res.update({ 'note': note } )			
			
        sale_order.write(res)	
        return True		

    def view_remote_erp_purchase(self, cr, uid, ids, context=None):
        xml_obj = xmlrpc_loewie()	
        for po in self.browse(cr, uid, ids, context=context):
            if po.remote_purchase_id > 0 :	 
                return {'type':'ir.actions.act_url', 'url':xml_obj._peer_purchase_redirect % (po.remote_purchase_id ), 'target':'new'}
					
		
class stock_picking(osv.osv):
    _inherit = "stock.picking"
	
    _columns = {
        'remote_picking_id': fields.integer( string='Remote Pick ID'),
        'picking_no':fields.char(string='Remote Pick NO'),		
    }
		
    def generate_sz_erp_picking(self, cr, uid, ids, context=None):	
        xml_obj = xmlrpc_loewie()	
        vals_move = {	
            'product_id': 0, #, 
            'product_uom_qty':0, 
            'location_dest_id':xml_obj.query_id_byname('stock.location', u'成品'), 
            'location_id':xml_obj.query_id_byname('stock.location', 'Suppliers'), 
            'company_id': 1, # xml_obj.query_id_byname('res.company', xml_obj._peer_company), 
            'date':datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'date_expected':(datetime.now() + timedelta(3)).strftime("%Y-%m-%d %H:%M:%S"), 
            'invoice_state':'none', 
            'name':'.', 
            'procure_method':'make_to_stock', 
            'state':'draft',			
            'product_uom':1, 
            'weight_uom_id':1,
            'picking_id': 0,			
        }		
		
        vals_pick = {
            'company_id': 1, # xml_obj.query_id_byname('res.company',xml_obj._peer_company),
            'partner_id': xml_obj.query_id_byname('res.partner',u'Loewie香港有限公司'), 	
            'create_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),			
            'origin': 'HK-PO',			
            #'invoice_state': 'none',			
            'move_type': 'direct',
            'picking_type_id': 1, #xml_obj.query_id_byname('stock.picking.type', u'Receipts(收货)'),			
            #'priority': 1,		
            #'weight_uom_id': 3,            			
        }		
	
        model1 = "stock.picking"		
        model2 = "stock.move"		
        method = "create" 		
	
        for order in self.browse(cr, uid, ids):
            if order.picking_type_id.code == 'incoming' : 			
                picking_type = 2 #xml_obj.query_id_byname('stock.picking.type', u'Receipts()')
            elif order.picking_type_id.code == 'outgoing' :
                picking_type = 1 #xml_obj.query_id_byname('stock.picking.type', u'Receipts(收货)')
            else:
                return 

            my_proxy = xmlrpclib.ServerProxy(xml_obj._peer_url)	
            remote_id = 0			
            if order.remote_picking_id:			
                remote_id = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model1, 'search', [('id','=',order.remote_picking_id)] )
			
            if remote_id :
                raise osv.except_osv(_(u'远端ERP仓库单据 已存在'),_(u'''请先删除远端ERP已生成的仓库单据：%s！！！''' % order.picking_no))					
				
            if True : #order.dest_address_id.name == xml_obj._company :			

                vals_pick.update({'origin': 'HK-Pick:%s' % order.name, 'picking_type_id':picking_type})				
                value = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model1,method, vals_pick )
                order.remote_picking_id = value		
                order.picking_no = my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model1, 'read', [value], ['name'] )[0]['name']
				
                if picking_type == 1 :    					
                    location_dest_id =  xml_obj.query_id_byname('stock.location', u'成品')                   					
                    location_id =  xml_obj.query_id_byname('stock.location', 'Suppliers')	
                if picking_type == 2 :    					
                    location_dest_id =  xml_obj.query_id_byname('stock.location', 'Suppliers')                   					
                    location_id =  xml_obj.query_id_byname('stock.location', u'成品')	
					
                un_created_products = []					
                for line in order.move_lines:
                    pid = xml_obj.query_product_id_by_name_template(line.product_id.name_template)					
					
                    if not pid:
                        if not line.product_id.ean13 and not line.product_id.default_code :  pid=0					
                        else: pid = xml_obj.query_product_id_by_ean13('product.product', line.product_id.ean13 or line.product_id.default_code)
								
                    if pid > 0 :	
                        vals_move.update({'product_id':pid, 'product_uom_qty':line.product_uom_qty, 'name': line.name, 'picking_id':value, 'location_dest_id':location_dest_id,  'location_id':location_id})	
                        my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model2, method, vals_move )
                    else:
                        un_created_products.append(line.product_id.name_template)
						
                if len(un_created_products) > 0:
                    names = ""				
                    for name in un_created_products:
                        names += name + " , " 					
                    order.note = ( order.note or "" ) + (u"   在远端ERP单据:%s 中无法找到与以下名字相同的产品：%s"  % (order.picking_no, names))
					
                    my_proxy.execute(xml_obj._db, 1, xml_obj._pwd, model1, 'write', value, {'note': u"远端ERP单据:%s 中的以下产品名 没有在本地ERP中创建: %s" % (order.name, names)} )
            return True	
					

    def view_sz_erp_picking(self, cr, uid, ids, context=None):
        xml_obj = xmlrpc_loewie()	
        for po in self.browse(cr, uid, ids, context=context):
            if po.remote_picking_id > 0 :	 
                return {'type':'ir.actions.act_url', 'url':xml_obj._peer_redirect % (po.remote_picking_id, po.picking_type_id.code=='incoming' and 2 or 1 ), 'target':'new'}		
						