# -*- coding: utf-8 -*-
import time
from openerp.report import report_sxw
from openerp.osv import osv
from openerp.tools.translate import _
import logging
import datetime
_logger = logging.getLogger(__name__)


class sale_report_libiya(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(sale_report_libiya, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr': cr,
            'uid': uid,
            'curr_line': self.curr_line,
            'curr_group': self.curr_group,
            'curr_rec': self.curr_rec,
            'compute_currency': self.compute_currency,
            'compute_currency_loewie': self.compute_currency_loewie,			
            'curr_group_value': self.curr_group_value,
            'order_discount': self._order_discount,
            'lines_group_by_brand_sample' : self.lines_group_by_brand_sample,
            'group_for_taiwan_custom' : self.group_for_taiwan_custom,
            'rounding':self.rounding,		
            'get_remark':self.get_remark,				
        })
		
    def rounding(self,number):
        str = "%0.3f" % number
        return 	str[:(len(str)-2)]


    def curr_rec(self, curr_ids):
        res = self.pool.get('res.currency').browse(self.cr, self.uid, curr_ids)
        return res.name

    def compute_currency(self, to_currency, from_currency, amt, context=None):
        if context is None:
            context = {}
        currency_obj = self.pool.get('res.currency')
        amount = currency_obj.compute(
            self.cr, self.uid, to_currency, from_currency, amt, context=context)
        return amount
		
    def compute_currency_loewie(self, to_currency, from_currency, amt, so_create_date=None, context=None):
        if context is None:
            context = {}

        currency_rate_obj = self.pool.get('res.currency.rate')
        to_r , from_r  = 1, 1, 
				
        if so_create_date: # and so_create_date.year < datetime.date.today().year or ( so_create_date and so_create_date.month < datetime.date.today().month ):
		
            so_create_days = ( (so_create_date.year-2000) * 12 + so_create_date.month ) * 30 + so_create_date.day
			
            if to_currency == from_currency:
                return amt
            if not to_currency	or not from_currency:
                return amt
				
            tt = 20480		
            to_rate = currency_rate_obj.search(self.cr, self.uid, [('currency_id', '=', to_currency)], context=context)	
            for rate in currency_rate_obj.browse(self.cr, self.uid, to_rate, context=context):
                rate_create_date = 	datetime.datetime.strptime(rate.create_date,"%Y-%m-%d %H:%M:%S").date()	
                rate_create_days = 	( (rate_create_date.year-2000) * 12 + rate_create_date.month ) * 30 + rate_create_date.day
                interval_days = so_create_days - rate_create_days			
				
                if interval_days == 0:
                    to_r = rate.rate		
                    break
					
                if interval_days < 0:
                    continue
					
                if tt > interval_days:
                    to_r = rate.rate				
                    tt = interval_days				

            tt = 20480		
            from_rate = currency_rate_obj.search(self.cr, self.uid, [('currency_id', '=', from_currency)], context=context)	
            for rate in currency_rate_obj.browse(self.cr, self.uid, from_rate, context=context):
                rate_create_date = 	datetime.datetime.strptime(rate.create_date,"%Y-%m-%d %H:%M:%S").date()			
                rate_create_days = ( (rate_create_date.year-2000) * 12 + rate_create_date.month ) * 30 + rate_create_date.day
                interval_days = so_create_days - rate_create_days	
				
                if interval_days == 0:
                    from_r = rate.rate		
                    break
					
                if interval_days < 0:
                    continue
					
                if tt > interval_days:
                    from_r = rate.rate				
                    tt = interval_days
        else:
            return self.compute_currency(to_currency, from_currency, amt)		
			
        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(self.cr, self.uid, 'Account')			

        return round((from_r/to_r)*amt,prec)
		
    def curr_group(self, order_line):
        ids = map(lambda x: x.id, order_line)
        t = {}
        self.cr.execute("select p.purchase_currency_id,t.type from \
                        sale_order_line as l\
                        LEFT JOIN product_product as p ON (l.product_id=p.id) \
                        LEFT JOIN sale_order as s  ON (l.order_id=s.id)\
                        LEFT JOIN product_template as t ON (p.product_tmpl_id=t.id) where l.id IN %s \
                        GROUP BY p.purchase_currency_id, t.type", (tuple(ids),))
        t = self.cr.fetchall()
        return t

    def curr_group_value(self, order):
        """
            group[0]: purchase_currency_id
            group[1]: product type
        """
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        sol_obj = self.pool.get('sale.order.line')

        res = {}

        order_line = order.order_line
        company_currency_id = order.company_id.currency_id.id
        order_curreny_id = order.currency_id.id
        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(self.cr, self.uid, 'Account')

        for line in order_line:
            if line.product_id.type == 'service':
                continue
            pur_cur_id = line.pur_currency_id.id # xie
            if not pur_cur_id:
                pur_cur_id = line.product_id and line.product_id.purchase_currency_id.id or company_currency_id

            if pur_cur_id != order_curreny_id:
            # line purchase currency is not order currency
                try:
                    if not pur_cur_id in res:
                        res[pur_cur_id] = {}
                        res[pur_cur_id].update({
                            'purchase_currency_id': line.pur_currency_id or line.product_id.purchase_currency_id,
                            'price_subtotal': 0,
                            'discount': 0,
                            'price_total': 0,
                            'price_subtotal_in_inv_cur': 0,
                            'lines': [],
                        })
                    price_unit = round(line.price_unit, prec)
                    price_total = round(self.compute_currency(
                            order_curreny_id, pur_cur_id,
                            round(price_unit * line.product_uom_qty, prec)), prec)

                    pur_price_unit = line.pur_price_unit
                    if not pur_price_unit:
                        pur_price_unit = round(self.compute_currency(
                            order_curreny_id, pur_cur_id, price_unit), prec)
                    pur_price_subtotal = line.pur_price_subtotal
                    if not pur_price_subtotal:
                        pur_price_subtotal = price_total
                    discount = round(pur_price_subtotal * line.discount / 100, prec)
                    price_subtotal = pur_price_subtotal - discount

                    line_value = {
                        'id': line.id,
                        'sequence': line.sequence,
                        'product_name': line.product_id.name,
                        'name': line.name,
                        'product_uom_qty': line.product_uom_qty,
                        'price_unit': pur_price_unit,
                        'discount': discount,
                        'discount_per': line.discount,
                        'price_total': pur_price_subtotal,
                    }

                    price_subtotal_in_inv_cur = round(price_unit * line.product_uom_qty * (1- line.discount / 100), prec)
                    res[pur_cur_id]['lines'].append(line_value)
                    res[pur_cur_id].update({
                        'discount': res[pur_cur_id]['discount'] + discount,
                        'price_total': res[pur_cur_id]['price_total'] + pur_price_subtotal,
                        'price_subtotal': res[pur_cur_id]['price_subtotal'] + price_subtotal,
                        'price_subtotal_in_inv_cur': res[pur_cur_id]['price_subtotal_in_inv_cur'] + price_subtotal_in_inv_cur,
                        })
                except:
                    pass
            else:
                # line purchase currency is order currency
                if order_curreny_id not in res:
                    res[order_curreny_id] = {}
                    res[order_curreny_id].update({
                        'purchase_currency_id': order.currency_id,
                        'price_subtotal': 0,
                        'discount': 0,
                        'price_total': 0,
                        'price_subtotal_in_inv_cur': 0,
                        'lines': []
                    })
                price_unit = round(line.price_unit, prec)
                price_total = round(price_unit * line.product_uom_qty, prec)
                discount = round(price_total * line.discount / 100, prec)
                price_subtotal = price_total - discount

                line_value = {
                    'id': line.id,
                    'product_name': line.product_id.name,
                    'name': line.name,
                    'product_uom_qty': line.product_uom_qty,
                    'price_unit': price_unit,
                    'discount': discount,
                    'discount_per': line.discount,
                    'price_total': price_total,
                }

                res[pur_cur_id]['lines'].append(line_value)
                res[pur_cur_id].update({
                    'discount': res[pur_cur_id]['discount'] + discount,
                    'price_total': res[pur_cur_id]['price_total'] + price_total,
                    'price_subtotal': res[pur_cur_id]['price_subtotal'] + price_subtotal,
                    'price_subtotal_in_inv_cur': res[pur_cur_id]['price_subtotal_in_inv_cur'] + price_subtotal,
                    })
        return res

    def _order_discount(self, order):
        res = {}
        service = []
        discount = 0
        price_subtotal = 0
        price_total = 0
        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(self.cr, self.uid, 'Account')

        for line in order.order_line:
            discount += round(line.price_unit * line.product_uom_qty, prec) - line.price_subtotal
            price_subtotal += line.price_subtotal
			
            if line.product_id.type == 'service':
                service_name = line.product_id.name			
                if line.name :
                    service_name += " " + line.name
					
                service.append((service_name, line.price_subtotal))
            else:
                price_total += round(line.price_unit * line.product_uom_qty, prec)

        res.update({
            'discount': discount,
            'price_subtotal': price_subtotal,
            'price_total': price_total,
            'other': [],
        })
        if service:
            res.update({'other': service})
        # res = [price_total, discount, price_subtotal]
        return res

    def curr_line(self, order_line):
        ids = map(lambda x: x.id, order_line)
        self.cr.execute("select l.id,l.name,p.purchase_currency_id,l.product_uom_qty,l.price_unit,l.discount,t.type from \
                        sale_order_line as l\
                        LEFT JOIN product_product as p ON (l.product_id=p.id)\
                        LEFT JOIN product_template as t ON (p.product_tmpl_id=t.id) \
                        LEFT JOIN sale_order as s  ON (l.order_id=s.id) where l.id IN %s \
                        GROUP BY l.product_uom_qty,l.price_unit,l.id,l.name,p.purchase_currency_id,l.discount,t.type", (tuple(ids),))
        t = self.cr.fetchall()
        return t

    def lines_group_by_brand_sample(self,order=None,move_lines=None,one_currency=False,half_price=False):        
        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(self.cr, self.uid, 'Account')        
        res_brand = {}
        result = {}		
        context = {}        
        company_currency_id = order.company_id.currency_id.id
        order_currency_id = order.currency_id.id

        order_line = order.order_line
        product_ids = {}
		
        use_purchase_currency = order.pricelist_id.use_purchase_currency       #jimmy 20160108 1637
        pricelist_currency = order.pricelist_id.currency_id.name

        if not order :
            raise osv.except_osv(_('No Sales Order!'),_('''No Sales Order related to this Delivery Order, So I cann't get the unit price of every product. '''))			
				
        for line in order_line:
            product_qty = line.product_uom_qty	
				
            type = line.product_id.product_type or ''
            type = type.strip()
            if line.name and line.name.lower().find('sample')>=0:
                type = 'Sample'			

            if line.name and line.name.lower().find('shortship')>=0:
                type = 'Shortship'	
				
            if line.name and line.name.lower().find('promotion')>=0:
                type = 'Promotion'
				
            if line.name and line.name.lower().find('replacement')>=0:
                type = 'Replacement'	

            if line.name and line.name.find('RMA')>=0:
                type = 'RMA'				
				
            if use_purchase_currency :			
                currency_name = line.pur_currency_id.name or line.product_id.purchase_currency_id.name
                brand_currency_id = line.pur_currency_id.id or line.product_id.purchase_currency_id.id  				
            else:
                currency_name = pricelist_currency	
                brand_currency_id = order.pricelist_id.currency_id.id		

            if order.partner_id.one_currency:  #客户结单时只用一种币种表示
                currency_name = pricelist_currency
                brand_currency_id = order.pricelist_id.currency_id.id		
                price_unit = line.price_unit
            else:
                price_unit = line.pur_price_unit
				
            if half_price: #
                price_unit = round(price_unit/2,prec)

            if type == 'Sample' and type == 'Shortship' and type == 'Replacement' :
                price_unit = 0			
				
            if type not in res_brand :
                res_brand[type]={}
                res_brand[type].update({
                    'type' : type,
                    'currency_name': currency_name, 
                    'currency_id': brand_currency_id, 					
                    'discount_rate': line.discount,					
                    'discount_amount':0,
                    'subtotal': 0,
                    'subtotal_without_discount': 0,
                    'subtotal_in_order_currency': 0,
                    'lines': [],  
                })
            
            price_total = round(product_qty * price_unit,prec)
            line_discount_amount = round(price_total * line.discount / 100,prec) 
			

            if not order.create_date:
                order_create_date = datetime.date.today()
            else:
                order_create_date = 	datetime.datetime.strptime(order.create_date,"%Y-%m-%d %H:%M:%S").date()        			
			
            #_logger.info("Jimmy0:%s" % order.order_create_date date_confirm)	
       			
            line_value = {
                'id': len(res_brand[type]['lines'])+1,
                'currency_name': currency_name,		
                'product_id': line.product_id.id,				 
                'product_name': line.product_id.name,
                'ean13': line.product_id.ean13,		
                'default_code': line.product_id.default_code,						
                'name': line.name,
                'product_uom_qty': product_qty,
                'discount_rate': line.discount,				
                'price_unit': price_unit,
                'line_discount_amount':	 line_discount_amount,	
                'total_without_discount_in_order_cur' : self.compute_currency_loewie(brand_currency_id,order_currency_id,round( price_total - line_discount_amount,prec ),order_create_date),				
                'price_total': price_total,
            }
				
            res_brand[type]['lines'].append(line_value)
            
            #calculate brand total
            price_total_set = map(lambda x:x['price_total'],res_brand[type]['lines'])			
				
            price_total_sum = sum(price_total_set)    
            discount_amount = sum(map(lambda x : x['line_discount_amount'], res_brand[type]['lines']))
            subtotal_without_discount = price_total_sum - discount_amount			
		
            if res_brand[type]['type'] == "Special Promotion" :
                subtotal_in_order_currency = sum(map(lambda x : x['total_without_discount_in_order_cur'], res_brand[type]['lines']))			
            else :			
                subtotal_in_order_currency = self.compute_currency_loewie(brand_currency_id,order_currency_id,round(subtotal_without_discount,prec),order_create_date)    
				
            res_brand[type].update({
                'subtotal':price_total_sum,
                'discount_amount' : discount_amount,
                'subtotal_without_discount' : subtotal_without_discount,                
                'subtotal_in_order_currency': subtotal_in_order_currency, 
            })
			
        if move_lines == None:			
            return res_brand		

        for line in move_lines:				
            type = line.product_id.product_type or ''
            type = type.strip()
            if line.name and line.name.lower().find('sample')>=0:
                type = 'Sample'			

            if line.name and line.name.lower().find('shortship')>=0:
                type = 'Shortship'	
				
            if line.name and line.name.lower().find('promotion')>=0:
                type = 'Promotion'
				
            if line.name and line.name.lower().find('replacement')>=0:
                type = 'Replacement'   
				
            if line.name and line.name.find('RMA')>=0:
                type = 'RMA'
				
            if type not in result :
                result[type]={}
                result[type].update({
                    'type' : type,
                    'currency_name': res_brand[type]['currency_name'],  
                    'discount_rate': res_brand[type]['discount_rate'],					
                    'discount_amount':0,
                    'subtotal': 0,
                    'subtotal_without_discount': 0,
                    'subtotal_in_order_currency': 0,
                    'qty_total': 0,				
                    'lines': [],  
                })
				
            product = None
            brand_currency_id = res_brand[type]['currency_id']
			
            for x in res_brand[type]['lines']:
                if x['product_id'] == line.product_id.id:
                    product = x	
                    break
            if product == None:
                raise osv.except_osv(_('Fucking !'),_('''Fucking You 2 '''))	
                #continue				
            				
				
            price_total = round(line.product_uom_qty * product['price_unit'],prec)
            line_discount_amount = round(price_total * product['discount_rate'] / 100,prec)
			
            line_val = {
                'id': len(result[type]['lines'])+1,
                'currency_name': res_brand[type]['currency_name'],	
                'product_id': line.product_id.id,				 
                'product_name': line.product_id.name,
                'name': line.name,
                'default_code': line.product_id.default_code,				
                'product_uom_qty': line.product_uom_qty,
                'discount_rate': product['discount_rate'],				
                'price_unit': product['price_unit'],
                'line_discount_amount':	 line_discount_amount,	
                'total_without_discount_in_order_cur' : self.compute_currency_loewie(brand_currency_id,order_currency_id,round( price_total - line_discount_amount,prec ),order_create_date),				
                'price_total': price_total,
            }
            #_logger.info("qty_on_the_way: %s", type)
            #_logger.info("qty_on_the_way: %s", line.product_id.name)	
            #_logger.info("qty_on_the_way: %d", line.product_uom_qty)	
	
		
            result[type]['lines'].append(line_val)
            
            #calculate brand total line_value
            price_total_set = map(lambda x:x['price_total'],result[type]['lines'])			
				
            price_total_sum = sum(price_total_set)    
            discount_amount = sum(map(lambda x : x['line_discount_amount'], result[type]['lines']))
            subtotal_without_discount = price_total_sum - discount_amount			
		
            if result[type]['type'] == "Special Promotion" :
                subtotal_in_order_currency = sum(map(lambda x : x['total_without_discount_in_order_cur'], result[type]['lines']))			
            else :			
                subtotal_in_order_currency = self.compute_currency_loewie(brand_currency_id,order_currency_id,round(subtotal_without_discount,prec),order_create_date)    
				
            result[type].update({
                'qty_total': result[type]['qty_total'] + line.product_uom_qty ,			
                'subtotal':price_total_sum,
                'discount_amount' : discount_amount,
                'subtotal_without_discount' : subtotal_without_discount,                
                'subtotal_in_order_currency': subtotal_in_order_currency, 
            })           		
			
        return result	

    def group_for_taiwan_custom(self,order,move_lines=None):        
        obj_precision = self.pool.get('decimal.precision')
        prec = obj_precision.precision_get(self.cr, self.uid, 'Account')        
        res_brand = {}  
        company_currency_id = order.company_id.currency_id.id
        order_currency_id = order.currency_id.id
        
        order_line = order.order_line       
        product_ids = {}
		
        use_purchase_currency = order.pricelist_id.use_purchase_currency       #jimmy 20160108 1637
        pricelist_currency = order.pricelist_id.currency_id.name
				
        if move_lines:		
            for move_line in move_lines:
                if move_line.product_id not in product_ids:			
                    product_ids[move_line.product_id] = {'qty':move_line.product_uom_qty,'read':0}
                else:
                    product_ids[move_line.product_id]['qty'] += move_line.product_uom_qty
				
        for line in order_line:
            product_qty = line.product_uom_qty		
            if move_lines :
                if (line.product_id in product_ids) and (product_ids[line.product_id]['read']==0) :		
                    product_qty = product_ids[line.product_id]['qty']		
                    product_ids[line.product_id]['read'] = 1					
                else:
                    continue
					
            type = line.product_id.product_type or ''
            type = type.strip()
            if line.name and line.name.lower().find('sample')>=0:
                type = 'Sample'			

            if line.name and line.name.lower().find('shortship')>=0:
                type = 'Shortship'	
				
            if line.name and line.name.lower().find('promotion')>=0:
                type = 'Promotion'
				
            if line.name and line.name.lower().find('replacement')>=0:
                type = 'Replacement'	 
				
            if line.name and line.name.find('RMA')>=0:
                type = 'RMA'
				
            if use_purchase_currency :			
                currency_name = line.pur_currency_id.name or line.product_id.purchase_currency_id.name
                brand_currency_id = line.pur_currency_id.id or line.product_id.purchase_currency_id.id  				
            else:
                currency_name = pricelist_currency	
                brand_currency_id = order.pricelist_id.currency_id.id		
				
            if type not in res_brand :
                res_brand[type]={}
                res_brand[type].update({
                    'type' : type,
                    'currency_name': currency_name,  
                    'discount_rate': line.discount,					
                    'discount_amount':0,
                    'subtotal': 0,
                    'subtotal_without_discount': 0,
                    'subtotal_in_order_currency': 0,
                    'lines': [],  
                })
            
            price_total = product_qty * round(line.price_unit/2,prec)	
            line_discount_amount = round(price_total * line.discount / 100)
			
            line_value = {
                'id': len(res_brand[type]['lines'])+1,
                'currency_name': currency_name,				
                'product_name': line.product_id.name,
                'ean13': line.product_id.ean13,					
                'product_class':line.product_id.product_class,
                'product_origin':line.product_id.product_origin,
                'product_material':line.product_id.product_material,
                'product_pic':(line.product_id.image_small != None and line.product_id.image_small or '' ),
                'product_format':line.product_id.product_format,				
                'product_uom_qty': product_qty,
                'discount_rate': line.discount,				
                'price_unit': round(line.price_unit/2,prec),
                'price_total': price_total,
                'line_discount_amount' : line_discount_amount,
            }
            
            res_brand[type]['lines'].append(line_value)
            
            #calculate brand total
            price_total_set = map(lambda x:x['price_total'],res_brand[type]['lines'])			
				
            price_total_sum = sum(price_total_set)    
            discount_amount = sum(map(lambda x : x['line_discount_amount'], res_brand[type]['lines']))
            subtotal_without_discount = price_total_sum - discount_amount			

            subtotal_in_order_currency = subtotal_without_discount # = self.compute_currency(brand_currency_id,order_currency_id,round(subtotal_without_discount,prec))
            
            res_brand[type].update({
                'subtotal':price_total_sum,
                'discount_amount' : discount_amount,
                'subtotal_without_discount' : subtotal_without_discount,                
                'subtotal_in_order_currency': subtotal_in_order_currency, 
            })
			
        return res_brand		

		
    def get_remark(self, order):		
        if order.note is None : 
            return False
			
        index = order.note.find('Remark:')	
        length = len('Remark:')		
        if index< 0 : 
            return False 	
        res = order.note[ (index+length) : len(order.note) ]
        res = res.replace('\n','<br/>')		
        return 	res	
		
		
class report_pos_details(osv.AbstractModel):
    _name = 'report.sale_webkit_report_loewie.report_sale_order_loewie'
    _inherit = 'report.abstract_report'
    _template = 'sale_webkit_report_loewie.report_sale_order_loewie'
    _wrapped_report_class = sale_report_libiya

class report_custom_details(osv.AbstractModel):
    _name = 'report.sale_webkit_report_loewie.report_sale_order_custom'
    _inherit = 'report.abstract_report'
    _template = 'sale_webkit_report_loewie.report_sale_order_custom'
    _wrapped_report_class = sale_report_libiya
	
class report_taiwan_details(osv.AbstractModel):
    _name = 'report.sale_webkit_report_loewie.report_sale_order_taiwan'
    _inherit = 'report.abstract_report'
    _template = 'sale_webkit_report_loewie.report_sale_order_taiwan'
    _wrapped_report_class = sale_report_libiya

class report_taiwan_wh(osv.AbstractModel):
    _name = 'report.sale_webkit_report_loewie.report_sale_order_taiwan_wh'
    _inherit = 'report.abstract_report'
    _template = 'sale_webkit_report_loewie.report_sale_order_taiwan_wh'
    _wrapped_report_class = sale_report_libiya

class report_custom_hk(osv.AbstractModel):
    _name = 'report.sale_webkit_report_loewie.report_sale_order_custom_hk'
    _inherit = 'report.abstract_report'
    _template = 'sale_webkit_report_loewie.report_sale_order_custom_hk'
    _wrapped_report_class = sale_report_libiya	
