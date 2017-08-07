# -*- coding: utf-8 -*-
import time
import string
from openerp.report import report_sxw
from openerp.osv import osv
import logging
_logger = logging.getLogger(__name__)

class stock_tmijdi_picking(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(stock_tmijdi_picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr': cr,
            'uid': uid,
            'group_lines_by_coe': self.group_lines_by_coe,				
        })		
		
    def group_lines_by_coe(self, o=None):	
        res = {}
        tmi_jdi_list = []		
        move_lines = o.move_lines.sorted(key=lambda r: r.coe_no)		
			
        for line in move_lines:
            product_name = line.product_id.name		
            if not line.coe_no : raise osv.except_osv(u"No COE Info",u'''Product Line:%s has No COE info''' % product_name)			
            coe_no = line.coe_no			
            coe_name = coe_no.name
            tmi_jdi_no = coe_no.tmi_jdi_no
			
            if coe_name not in res.keys():
                res[coe_name] = {}    				
                if tmi_jdi_no not in tmi_jdi_list: tmi_jdi_list.append(tmi_jdi_no)	
				
                note = u"%s, COE:%s , 姓名:%s , 电话:%s , 省份:%s , 城市:%s , 收货地址:%s , 邮编:%s ;"	% (tmi_jdi_no, coe_no.name, coe_no.receive_name, coe_no.tel, coe_no.province,coe_no.city,coe_no.address,coe_no.zip )				
                res[coe_name].update({
                'coe_info':note,				
                'lines':[], 
                })				
            else:				
                if tmi_jdi_no not in tmi_jdi_list: 
                    tmi_jdi_list.append(tmi_jdi_no)
                    res[coe_name]['coe_info'] = tmi_jdi_no + "/" + res[coe_name]['coe_info']					
				
            availability = 0				
            if line.picking_type_id.code == 'incoming' and line.state != 'done':
                availability = line.product_uom_qty
            else:
                availability = line.reserved_availability
				
            loc_src = line.location_id.name
            loc_dest = line.location_dest_id.name			
			
            if line.picking_type_id.code == 'outgoing':			 
                if line.product_id.is_sample: loc_src = 'Sample Loc'
                if line.product_id.clean_inventory: loc_src = 'Clean Loc'
                if line.product_id.is_market: loc_src = 'Market Loc'				
			
            if line.picking_type_id.code == 'incoming':			 
                if line.product_id.is_sample: loc_dest = 'Sample Loc'
                if line.product_id.clean_inventory: loc_dest = 'Clean Loc'
                if line.product_id.is_market: loc_dest = 'Market Loc'
				
            line_value = {
                'id': len(res[coe_name]['lines'])+1,			
                'product_name': product_name,		
                'description': line.name,				
                'internal_reference':line.product_id.default_code,
                'coe_no':line.coe_no.name,		
                'tmi_jdi_no':tmi_jdi_no,				
                'loc_dest': loc_dest,				
                'loc_src': loc_src,				
                'ean13':line.product_id.ean13,				
                'qty': line.product_uom_qty,				
                'availability': availability,				
            }
			
            res[coe_name]['lines'].append(line_value)		
			
        return res			
		
class tmijdi_picklist_details(osv.AbstractModel):
    _name = 'report.loewieec_sync_hk.stock_picking_tmijdi'
    _inherit = 'report.abstract_report'
    _template = 'loewieec_sync_hk.stock_picking_tmijdi'
    _wrapped_report_class = stock_tmijdi_picking
	
	