# -*- encoding: utf-8 -*-
from openerp.osv import fields,osv
from openerp import tools
from xml.dom.minidom import Document
from datetime import datetime, timedelta
from CoeRequest import CoeRequest
import StringIO
import os
import re
import uuid


class productProduct(osv.osv):
    _inherit = "product.product"
    _columns = {
        'coe_weight':fields.float('Coe Weight'),		
        'coe_class': fields.char('Coe Class'),
    }
	
class sale_order(osv.osv):
    _inherit = "sale.order"
	
    _columns = {	
        'selected': fields.boolean('Selected'),	
        'shop_id': fields.many2one('loewieec.shop', string=u"EC店铺名", readonly=True),
        'sale_code': fields.char(u'EC单号', readonly=True),	
    }
	
    def split_address(self, address):
        assert address != None
        addr_list = address.split(" ",2)		
        if len(addr_list) < 3: return None	
		
        addr = addr_list[2].split("(",1)
        if len(addr) < 2: return None	
		
        zip = addr[1].split(")")
        if len(zip)<1 : return None
		
        return {'province':addr_list[0],'city':addr_list[1],'address':addr[0],'zip':zip[0]}				
		
    def get_full_path(self, cr, uid, path):
        # sanitize ath
        path = re.sub('[.]', '', path)
        path = path.strip('/\\')
        return os.path.join(tools.config.filestore(cr.dbname), path)		
	
    def import_tmall_csv_file(self, cr, uid, ids, context=None):

        attachment_obj = self.pool.get('ir.attachment')
        shop_attach_id = context.get('res_id')	
        shop_attach_id = shop_attach_id or ids[0]		
        attachment_id = attachment_obj.search(cr,uid,[('res_id', '=', shop_attach_id)], context=context)		
        if len(attachment_id)<1: return False
        attach = attachment_obj.browse(cr,uid,attachment_id[0],context=context)
        fname = attach.store_fname
        display_name = attach.name		
        if not fname : return False		
        fname = self.get_full_path(cr, uid, fname)	
		
        csvfile = file(fname, 'rb')		
        #reader = csv.reader(csvfile)
		
        coe_obj = self.pool.get('sale.coe')    		
        tmi_no = {}
        no_coe_list = []		
        		
        sale_id = ids[0]
        #for line in reader:
        for line in csvfile.readlines():		
            line = line.decode('gbk')
            line = line.split(",")			
            if line[0] == u'订单编号' and line[1] == u'买家会员名' :	 continue

            coeids = coe_obj.search(cr,uid,[('tmi_jdi_no','=',line[0])],context=context)
            coeid = coeids and coeids[0] or 0				
            if not coeid : 	
                addr = self.split_address(line[13])					
                if addr : coe_info = {'tmi_jdi_no':line[0], 'name':line[1], 'receive_name':line[12], 'tel':line[16], 'address':addr['address'], 'province':addr['province'], 'city':addr['city'], 'zip':addr['zip']}
                else: coe_info = {'tmi_jdi_no':line[0], 'name':line[1], 'receive_name':line[12], 'tel':line[16], 'address':line[13]}				
                coeid = coe_obj.create( cr, uid, coe_info, context=context )
 
            tmi_no[line[0]] = coeid
			
        sale_order = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)
        coe_in_sale = []		
        for line in sale_order.order_line:
            tmi_jdi_no = line.tmi_jdi_no
            if not tmi_jdi_no : continue
			
            if tmi_jdi_no in tmi_no.keys():
                line.coe_no = tmi_no[tmi_jdi_no]
                coe_in_sale.append(tmi_jdi_no)				
                #tmi_no[tmi_jdi_no] = 0	 # 这里有问题， 如果一个 电商订单有几个产品，则只有第一个产品行 会被添加 coe 条目id			
            else:			
                no_coe_list.append(tmi_jdi_no) 

        if no_coe_list : 
            log = sale_order.note or ''		
            sale_order.note = u'以下TMI订单无COE信息:' + chr(10) + ",".join(no_coe_list) + chr(10) + log
			
        not_in_tmi_no = []
        for key in tmi_no.keys():
            if key not in  coe_in_sale: not_in_tmi_no.append(key)
			
        if not_in_tmi_no : 
            #log = sale_order.note or ''		
            sale_order.note = ",".join( not_in_tmi_no ) # + chr(10) + log	  #  u'以下CSV 收货人信息 无法匹配到 订单行:' + chr(10) +  

    def calculate_coe_qty_weight_price_desc(self, coe_objs=None):	
	
        # 首先分组
        res = {}
        for obj in coe_objs:
            key = (obj.tel or '').strip() + (obj.receive_name or '').strip() + (obj.address or '').strip()		
            if key not in res.keys():
                res[key] = [obj]	
            else:
                res[key].append(obj)
				
        return res
		
        # 接下来 计算 qty, weight, price, class_desc  ,,<--- 不需要这样做      	
        """		
        for key in res.keys():
            length = len( res[key] )		
            if length < 2 : continue		
            for val in res[key][1:length] : 
                res[key][0].qty += 	val.qty		
                res[key][0].price += val.price	
                res[key][0].class_desc += "," + val.class_desc	
                res[key][0].weight += val.weight					
		
        return res    """

    def cancel_coe_no_for_lines(self, cr, uid, ids, context=None):	
	
        cr.execute( "select coe_no from sale_order_line where order_id=%d group by coe_no" % ids[0] )
        coeno_list = [ item[0] for item in cr.fetchall() ]
        error_list = []
        coe_request = CoeRequest()	
		
        for coe in self.pool.get('sale.coe').browse(cr, uid, coeno_list, context=context):
		
            coe_no = coe.name or ''	
            if coe_no.find('EL') < 0 or coe_no.find('HK') < 0 : continue		
			
            xml_obj = self.cancel_request_xml( coe_no )			
            buff = StringIO.StringIO('')
            xml_obj.writexml(buff)
            buff.seek(0)
            xml = buff.buf.strip()
            xml = xml.replace('<?xml version="1.0" ?>','')			
            result = coe_request.getCancelResponse( xml )
			
            if result['success'] :  
                coe.name = coe.receive_name
            else:
                error_list.append(coe_no)

        if error_list :
            saleorder = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)		
            log = saleorder.note or ''
            saleorder.note = u'以下COE运单号未能取消: ' + chr(10) + ','.join(error_list) + chr(10) + log	            		
				
    def get_coe_no_for_lines(self, cr, uid, ids, context=None):	
		
        statement1 = "select s.coe_no as coe_no, s.product_uom_qty as qty, p.coe_weight as weight, p.coe_class as desc from sale_order_line s left join product_product p on s.product_id=p.id where order_id=%d and p.is_sample=False" % ids[0]	
		
        statement = "select coe_no from sale_order_line where order_id=%d group by coe_no" % ids[0]		
        coe_products = {}
        coe_ids = []		
        cr.execute(statement)
        for coe in cr.fetchall():
            if coe[0] not in coe_ids: 
                coe_ids.append(coe[0])		
            if coe[0] not in coe_products.keys(): 	
                coe_products[coe[0]] = [ [coe[1],coe[2],coe[3]] ]
            else : 			
                coe_products[coe[0]].append([coe[1],coe[2],coe[3]])			
		
        # 计算 COE分组
        coe_objs = self.pool.get('sale.coe').browse(cr,uid,sorted(coe_ids),context=context)
        coe_dict2 = self.calculate_coe_qty_weight_price_desc(coe_objs)		
		
        coe_request = CoeRequest()		
        error_list = ''
		
        for key in coe_dict2.keys() : 
            coe_list = coe_dict2[key]
            coe = coe_list[0]			
            if coe.name.find('EL') >= 0 and coe.name.find('HK') > 0 : continue
            xml_obj = self.generate_request_xml(coe_list, coe_products)			
            buff = StringIO.StringIO('')
            xml_obj.writexml(buff)
            buff.seek(0)
            xml = buff.buf.strip()
            xml = xml.replace('<?xml version="1.0" ?>','')			
            xml = xml.encode("utf-8")			
            result = coe_request.getResponse( '' )
			
            if result['success'] :  
                coe.name = result['trackingNo']	
            else:
                error_list += coe.tmi_jdi_no + ' - ' + result['msg'] + chr(10)	
				
        if error_list :	
            saleorder = self.pool.get('sale.order').browse(cr,uid,ids[0],context=context)		
            log = saleorder.note or ''
            saleorder.note = error_list + log			

    def generate_request_xml(self, coe_list, products):
	
        assert coe_list != None
        coe = coe_list[0]
        coe_ids = [ o.id for o in coe_list ]
	
        doc = Document()
		
        logisticsEventsRequest = doc.createElement('logisticsEventsRequest') 
        doc.appendChild(logisticsEventsRequest)		
        logisticsEvent = doc.createElement('logisticsEvent')		
		
        eventHeader = doc.createElement('eventHeader')
        logisticsEventsRequest.appendChild(logisticsEvent)
        logisticsEvent.appendChild(eventHeader)		
		
        eventType = doc.createElement('eventType')
        eventType_val = doc.createTextNode('COE_ETK_ORDER_CREATE')
        eventType.appendChild(eventType_val)
        eventHeader.appendChild(eventType)		
		
        eventTime = doc.createElement('eventTime')
        eventTime_val = doc.createTextNode( (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')   )
        eventTime.appendChild(eventTime_val)		
        eventHeader.appendChild(eventTime) 
		
        eventMessageId = doc.createElement('eventMessageId')
        msg_val = doc.createTextNode( str( uuid.uuid1() ) )
        eventMessageId.appendChild(msg_val)		
        eventHeader.appendChild(eventMessageId) 
		
        eventSource = doc.createElement('eventSource')
        eventSource_val = doc.createTextNode( 'Loewie Trading Ltd.' )
        eventSource.appendChild(eventSource_val)		
        eventHeader.appendChild(eventSource) 
		
        eventTarget = doc.createElement('eventTarget')
        eventTarget_val = doc.createTextNode('ETK')
        eventTarget.appendChild(eventTarget_val)		
        eventHeader.appendChild(eventTarget) 
		
        eventBody = doc.createElement('eventBody')
        logisticsEvent.appendChild(eventBody)	
		
        order = doc.createElement('order')
        eventBody.appendChild(order)
		
        referenceId = doc.createElement('referenceId')
        referenceId_val = doc.createTextNode( str(coe.tmi_jdi_no) )
        referenceId.appendChild(referenceId_val)		
        order.appendChild(referenceId)
		
        customerNo = doc.createElement('customerNo')
        customerNo_val = doc.createTextNode( 'ECM1993ZHK' )
        customerNo.appendChild(customerNo_val)		
        order.appendChild(customerNo)
		
        receiver = doc.createElement('receiver')		
        order.appendChild(receiver)
		
        receiverName = doc.createElement('receiverName')
        receiverName_val = doc.createTextNode( coe.receive_name )
        receiverName.appendChild(receiverName_val)		
        receiver.appendChild(receiverName)
		
        receiverAddress1 = doc.createElement('receiverAddress1')
        receiverAddress1_val = doc.createTextNode( coe.address )
        receiverAddress1.appendChild(receiverAddress1_val)		
        receiver.appendChild(receiverAddress1)
		
        receiverCity = doc.createElement('receiverCity')
        receiverCity_val = doc.createTextNode( coe.city )
        receiverCity.appendChild(receiverCity_val)		
        receiver.appendChild(receiverCity)
		
        receiverProvince = doc.createElement('receiverProvince')
        receiverProvince_val = doc.createTextNode( coe.province )
        receiverProvince.appendChild(receiverProvince_val)		
        receiver.appendChild(receiverProvince)
		
        receiverPhone = doc.createElement('receiverPhone')
        receiverPhone_val = doc.createTextNode( coe.tel )
        receiverPhone.appendChild(receiverPhone_val)		
        receiver.appendChild(receiverPhone)		
		
        receiverCode = doc.createElement('receiverCode')
        receiverCode_val = doc.createTextNode( coe.zip )
        receiverCode.appendChild(receiverCode_val)		
        receiver.appendChild(receiverCode)		
		
        sender  = doc.createElement('sender')		
        order.appendChild(sender )		
		
        senderCurrency  = doc.createElement('senderCurrency')
        senderCurrency_val = doc.createTextNode('RMB')
        senderCurrency .appendChild(senderCurrency_val)		
        sender.appendChild(senderCurrency )
		
        senderName = doc.createElement('senderName')
        senderName_val = doc.createTextNode('LOEWIE TRADING Ltd.')
        senderName.appendChild(senderName_val)		
        sender.appendChild(senderName)
		
        senderPhone  = doc.createElement('senderPhone')
        senderPhone_val = doc.createTextNode('+852-3996.7967')
        senderPhone .appendChild(senderPhone_val)		
        sender.appendChild(senderPhone )		
		
        senderAddress = doc.createElement('senderAddress')
        senderAddress_val = doc.createTextNode("20/F Central Tower, 28 Queen's Road, Central, Hong Kong")
        senderAddress.appendChild(senderAddress_val)		
        sender.appendChild(senderAddress)		
		
        items  = doc.createElement('items')		
        order.appendChild(items )			
		
        for coe_id in coe_ids :
		
            for product in products[ coe_id ] :
			
                item  = doc.createElement('item')	   # qty,weight,desc,price	
                items.appendChild(item )	
				
                itemDescription  = doc.createElement('itemDescription')
                itemDescription_val = doc.createTextNode( product[2] )
                itemDescription .appendChild(itemDescription_val)		
                item.appendChild(itemDescription )
		
                itemQuantity = doc.createElement('itemQuantity')
                itemQuantity_val = doc.createTextNode( str(product[0]) )
                itemQuantity.appendChild(itemQuantity_val)		
                item.appendChild(itemQuantity)
		
                itemPrice  = doc.createElement('itemPrice')
                itemPrice_val = doc.createTextNode( str( product[3] ) )
                itemPrice .appendChild(itemPrice_val)		
                item.appendChild(itemPrice )		
		
                itemWeight = doc.createElement('itemWeight')
                itemWeight_val = doc.createTextNode( str( product[1] ) )
                itemWeight.appendChild(itemWeight_val)		
                item.appendChild(itemWeight)

        return doc		
		
    def cancel_request_xml(self, coe_no):
        doc = Document()
		
        logisticsEventsRequest = doc.createElement('logisticsEventsRequest') 
        doc.appendChild(logisticsEventsRequest)		
        logisticsEvent = doc.createElement('logisticsEvent')		
		
        eventHeader = doc.createElement('eventHeader')
        logisticsEventsRequest.appendChild(logisticsEvent)
        logisticsEvent.appendChild(eventHeader)		
		
        eventType = doc.createElement('eventType')
        eventType_val = doc.createTextNode('COE_ETK_ORDER_CANCEL')
        eventType.appendChild(eventType_val)
        eventHeader.appendChild(eventType)		
		
        eventMessageId = doc.createElement('eventMessageId')
        msg_val = doc.createTextNode( str( uuid.uuid1() ) )
        eventMessageId.appendChild(msg_val)		
        eventHeader.appendChild(eventMessageId) 		
		
        eventTime = doc.createElement('eventTime')
        eventTime_val = doc.createTextNode( (datetime.now() + timedelta(hours=8)).strftime('%Y-%m-%d %H:%M:%S')   )
        eventTime.appendChild(eventTime_val)		
        eventHeader.appendChild(eventTime) 		
		
        eventSource = doc.createElement('eventSource')
        eventSource_val = doc.createTextNode( 'Loewie Trading Ltd.' )
        eventSource.appendChild(eventSource_val)		
        eventHeader.appendChild(eventSource) 
		
        eventTarget = doc.createElement('eventTarget')
        eventTarget_val = doc.createTextNode('ETK')
        eventTarget.appendChild(eventTarget_val)		
        eventHeader.appendChild(eventTarget) 
		
        eventBody = doc.createElement('eventBody')
        logisticsEvent.appendChild(eventBody)	
		
        customerNo = doc.createElement('customerNo')
        customerNo_val = doc.createTextNode( 'ECM1993ZHK' )
        customerNo.appendChild(customerNo_val)		
        eventBody.appendChild(customerNo)
		
        trackingNo = doc.createElement('trackingNo')
        trackingNo_val = doc.createTextNode( coe_no )
        trackingNo.appendChild(trackingNo_val)		
		
        eventBody.appendChild( trackingNo )	
		
        return doc	