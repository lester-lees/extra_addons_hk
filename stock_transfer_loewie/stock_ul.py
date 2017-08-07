# -*- coding: utf-8 -*-
from openerp.osv import osv, fields, expression
from openerp.tools.translate import _
import logging
_logger = logging.getLogger(__name__)

class product_ul(osv.osv):
    _name = "product.ul"
    _inherit = "product.ul"
    _columns = {
        'type' : fields.selection([('unit','Unit'),('pack','Pack'),('box', 'Box'), ('pallet', 'Pallet')], 'Type', required=True),
    }
    _defaults = {
        'type': 'box',
    }
	
	
class stock_package(osv.osv):
    _name = "stock.quant.package"
    _inherit = "stock.quant.package"
	
    _columns = {
        'picking_id' : fields.many2one('stock.picking', 'Picking ID', ),	
    }	
	
class stock_picking(osv.osv):
    _name = "stock.picking"
    _inherit = ['stock.picking']	
		
    def _get_saleorder_id(self, cr, uid, ids, name, args, context=None):
        sale_obj = self.pool.get("sale.order")
        res = {}
        for picking in self.browse(cr, uid, ids, context=context):
            res[picking.id] = False
            if picking.group_id:
                sale_ids = sale_obj.search(cr, uid, [('procurement_group_id', '=', picking.group_id.id)], context=context)
                if sale_ids:
                    res[picking.id] = sale_ids[0]
        return res
    
    _columns = {
        'salesorder_id': fields.function(_get_saleorder_id, type="many2one", relation="sale.order", string="Sale Order ID", store=True),
        'packages_ids':fields.one2many('stock.quant.package', 'picking_id', string='Related Packages'),	
        }		

    def show_so_delivery(self, cr, uid, ids, context=None):		

        picks = []	
        act_obj = self.pool.get('ir.actions.act_window')
        statement = """select id from stock_picking where group_id in (select procurement_group_id from sale_order where user_id=%d)"""  % uid		
        cr.execute(statement)
		
        for i in cr.fetchall():
            picks.append(i[0])	
			
        result = act_obj.read(cr, uid, [483], context={})[0]
        if ids == 0:		
            result['domain'] = "[ '&', ('state','not in',['done','draft','cancel']), ('id','in',[" + ','.join(map(str, picks)) + "])]"	
        elif  ids == 1:
            result['domain'] = "[ '&', ('state','=','done'), ('id','in',[" + ','.join(map(str, picks)) + "])]"		
		
        return result		
