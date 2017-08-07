# -*- coding: utf-8 -*-
import time
import string
from openerp.report import report_sxw
from openerp.osv import osv
import logging
_logger = logging.getLogger(__name__)

class stock_report_picking(report_sxw.rml_parse):

    def __init__(self, cr, uid, name, context):
        super(stock_report_picking, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr': cr,
            'uid': uid,
            'group_op_lines': self.group_op_lines,
            'group_mv_lines': self.group_mv_lines,	
            'group_lines': self.group_lines,				
        })
		
    def _get_subordinate_ids(uid):
        res = []	
		
        sections_obj = 	self.pool.get('crm.case.section')
        users_obj = self.pool.get('res.users')	
		
    def group_op_lines(self, o = None):	
        res = {}
        operation_ids = o.pack_operation_ids				
        for line in operation_ids:
            package_no = ''		
			
            if line.result_package_id.name : 
                strTmp = line.result_package_id.name.split("x")
                package_no_str = strTmp[len(strTmp)-1].strip()				
                package_no = string.atoi( package_no_str )				

            if package_no not in res:
                res[package_no] = {}
                res[package_no].update({
                'package_no':package_no,
                'weight': line.result_package_id.package_weight,			
                'dimension': line.result_package_id.ul_id.name,		
                'lines':[],
                })
 
            line_value = {
                'product_name': line.product_id.name,
                'ean13': line.product_id.ean13,
                'code':	line.product_id.default_code,				
                'qty': line.product_qty,				
            }
            res[package_no]['lines'].append(line_value)			
			
        return res			
		
    def group_mv_lines(self, move_lines = None):	
        res = {}
				
        for line in move_lines:
            type = ''
			
            if line.product_id.product_type : 
                type = line.product_id.product_type
				
            if line.product_id.product_type == 'Service' : continue
            if type not in res:
                res[type] = {}
                res[type].update({
                'type':type,
                'lines':[],
                })

            availability = 0				
            if line.picking_type_id.code == 'incoming' and line.state != 'done':
                availability = line.product_uom_qty
            else:
                availability = line.reserved_availability
				
            loc_src = line.location_id.name
            loc_dest = line.location_dest_id.name			
			
            if line.picking_type_id.code == 'outgoing':			 
                if line.product_id.is_sample: loc_src = 'Sample Loc'
                if line.product_id.clean_inventory or line.product_id.is_clean_inventory : loc_src = 'Clean Loc'
                if line.product_id.is_market: loc_src = 'Market Loc'				
			
            if line.picking_type_id.code == 'incoming':			 
                if line.product_id.is_sample: loc_dest = 'Sample Loc'
                if line.product_id.clean_inventory or line.product_id.is_clean_inventory : loc_dest = 'Clean Loc'
                if line.product_id.is_market: loc_dest = 'Market Loc'
				
            line_value = {
                'id': len(res[type]['lines'])+1,			
                'product_name': line.product_id.name,		
                'description': line.name,				
                'internal_reference':line.product_id.default_code,
                'loc_dest': loc_dest,				
                'loc_src': loc_src,				
                'ean13':line.product_id.ean13,				
                'qty': line.product_uom_qty,				
                'availability': availability,				
            }
            res[type]['lines'].append(line_value)			
			
        return res		
		
    def group_lines(self, order):
        order_lines = order.order_lines	
        res = {}
				
        for line in order_lines:
            type = ''	
            if line.product_id.product_type == 'Service' : continue			
            if line.product_id.product_type : type = line.product_id.product_type
            if type not in res:
                res[type] = {}
                res[type].update({
                'type':type,
                'lines':[],
                })
 
            line_value = {
                'id': len(res[type]['lines'])+1,			
                'product_name': line.product_id.name,
                'internal_reference':line.product_id.default_code,				
                'ean13':line.product_id.ean13,					
                'qty': line.product_uom_qty,				
            }
            res[type]['lines'].append(line_value)			
			
        return res        		
	
class report_picklist_details(osv.AbstractModel):
    _name = 'report.stock_picking_loewie.stock_picking_loewie'
    _inherit = 'report.abstract_report'
    _template = 'stock_picking_loewie.stock_picking_loewie'
    _wrapped_report_class = stock_report_picking
	

class report_qo_picklist(osv.AbstractModel):
    _name = 'report.stock_picking_loewie.report_picklist'
    _inherit = 'report.abstract_report'
    _template = 'stock_picking_loewie.report_picklist'
    _wrapped_report_class = stock_report_picking		
	
	
class report_packlist_details(osv.AbstractModel):
    _name = 'report.stock_picking_loewie.stock_packing_loewie'
    _inherit = 'report.abstract_report'
    _template = 'stock_picking_loewie.stock_packing_loewie'
    _wrapped_report_class = stock_report_picking	