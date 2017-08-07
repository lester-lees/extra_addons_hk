# -*- coding: utf-8 -*- manager_confirm_btn
from openerp.osv import fields, osv
import logging
_logger = logging.getLogger(__name__)
	
class sale_order(osv.osv):
    _inherit = 'sale.order'	

    def _undelivered_get(self, cr, uid, ids, field_name, arg, context=None):
        res = {}
		
        for so in self.browse(cr, uid, ids, context=context):
            undeliveryed_pick = ""		
            for pick in so.picking_ids:
                if pick.state in ['assigned','confirmed','partially_available']  : 
                    if undeliveryed_pick != "" : 
                        undeliveryed_pick += "," + pick.name	
                    else: 
                        undeliveryed_pick = pick.name					
            res[so.id] = undeliveryed_pick
        return res		
		
    _columns = {
        'undelivered': fields.function(_undelivered_get, type="char", copy=False, string='Undelivered', readonly=True, select=True ),		
    }
	
	