# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
import logging
from openerp import api
from openerp.tools.float_utils import float_compare, float_round
from openerp.tools.translate import _

_logger = logging.getLogger(__name__)


class stock_picking_type(osv.osv):
    _inherit = "stock.picking.type"
    _columns = {
        'display': fields.boolean(string="Display?"),	
    }

class stock_pack_operation(osv.osv):
    _inherit = "stock.pack.operation"
	
    def split_quantities(self, cr, uid, ids, context=None ):	
	
        for operation in self.browse(cr, uid, ids, context=context):
		
            tmp_qty = operation.product_qty
            qty = int(tmp_qty/2)			
            if tmp_qty > 1 :
		
                operation.product_qty = qty
                new_id = operation.copy( default = {'product_qty':int(tmp_qty - qty)} )	
			

class stock_quant(osv.osv):

    def _get_so_id(self, cr, uid, ids, field_names=None, arg=False, context=None):    
        res = {}       
        reserv_objs = self.pool.get('stock.reservation')

        for quant in self.browse(cr, uid, ids, context=context):
            res[quant.id] = quant.reservation_id.picking_id.sale_id.name
            if not quant.reservation_id.picking_id.sale_id:
                _logger.info("Jimmy:%d" % quant.reservation_id.id)				
                reserv_id = reserv_objs.search(cr, uid,  [('move_id', '=', quant.reservation_id.id)], context=context)
                if not reserv_id :	
                    continue				
                reserv = reserv_objs.browse(cr, 1, [reserv_id[0]], context=context)				
                res[quant.id] = reserv.sale_line_id.order_id.name
                #_logger.info(reserv.sale_line_id.order_id.name)				
			
        return res	

    def _get_so_user_id(self, cr, uid, ids, field_names=None, arg=False, context=None):    
        res = {}        
        reserv_objs = self.pool.get('stock.reservation')
		
        for quant in self.browse(cr, uid, ids, context=context):
            res[quant.id] = quant.reservation_id.picking_id.sale_id.user_id.login
            if not quant.reservation_id.picking_id.sale_id:
                _logger.info("Jimmy:%d" % quant.reservation_id.id)				
                reserv_id = reserv_objs.search(cr, uid,  [('move_id', '=', quant.reservation_id.id)], context=context)
                if not reserv_id :	
                    continue				
                reserv = reserv_objs.browse(cr, 1, [reserv_id[0]], context=context)				
                res[quant.id] = reserv.sale_line_id.order_id.user_id.login
                #_logger.info(reserv.sale_line_id.order_id.user_id.login)				
        return res			
		
    _inherit = "stock.quant"
    _columns = {
        'so_id': fields.function(_get_so_id, type='char',string="Sale Order"),
        'so_user_id': fields.function(_get_so_user_id, type='char',string="Sales Person"), 	#fields.char("Sales Person"),	
    }	

	
class stock_quant_package_ext(osv.osv):
    _inherit = "stock.quant.package"
    _columns = {
        'dimension': fields.char('Dimension', size=16),
        'package_weight': fields.float('Weight'),
    }


class stock_move(osv.osv):
    _inherit = "stock.move"
	
    def _get_cost(self, cr, uid, ids, field_names=None, arg=False, context=None):   
        res = {}  	
        for move in self.browse(cr, uid, ids, context=context):	
            if move.purchase_line_id:
                res[move.id] = move.purchase_line_id.price_unit
            else:
                res[move.id] = move.product_id.standard_price			
        return res		

    def _get_hksz_total(self, cr, uid, ids, field_names=None, arg=False, context=None):
        res = {}  	
        for move in self.browse(cr, uid, ids, context=context):
            res[move.id] = move.product_uom_qty * move.price_hk_sz_exchange

        return res			
		
    _columns = {	
        'cost': fields.function(_get_cost, type='float', string='Cost'),
        'price_hk_sz_exchange': fields.related('product_id','price_hk_sz_exchange',readonly=True, type='float',string='Exchange Price'),
        'price_total_hksz': fields.function(_get_hksz_total , type='float', string='Price Total'),		
        'produce_bill_id':fields.integer('Produce Bill'),
        'is_checked':fields.boolean(string=u'选择行', default=False, copy=False),	
        'location_id': fields.many2one('stock.location', 'Src Loc', required=True, select=True, states={'done': [('readonly', True)]}, help="Sets a location if you produce at a fixed location. This can be a partner location if you subcontract the manufacturing operations."),
        'location_dest_id': fields.many2one('stock.location', 'Dest Loc', required=True, states={'done': [('readonly', True)]}, select=True, help="Location where the system will stock the finished products."),	
        }

		
    def onchange_product_id(self, cr, uid, ids, prod_id=False, loc_id=False, loc_dest_id=False, partner_id=False):

        if not prod_id:
            return {}
        user = self.pool.get('res.users').browse(cr, uid, uid)
        lang = user and user.lang or False
        if partner_id:
            addr_rec = self.pool.get('res.partner').browse(cr, uid, partner_id)
            if addr_rec:
                lang = addr_rec and addr_rec.lang or False
        ctx = {'lang': lang}

        product = self.pool.get('product.product').browse(cr, uid, [prod_id], context=ctx)[0]
        uos_id = product.uos_id and product.uos_id.id or False
        result = {
            'name': product.description_sale or '.',
            'product_uom': product.uom_id.id,
            'product_uos': uos_id,
            #'product_uom_qty': 1.00,
            'product_uos_qty': self.pool.get('stock.move').onchange_quantity(cr, uid, ids, prod_id, 1.00, product.uom_id.id, uos_id)['value']['product_uos_qty'],
        }
        if loc_id:
            result['location_id'] = loc_id
        if loc_dest_id:
            result['location_dest_id'] = loc_dest_id
        return {'value': result}


    def action_scrap(self, cr, uid, ids, quantity, location_id, restrict_lot_id=False, restrict_partner_id=False, context=None):
        """ Move the scrap/damaged product into scrap location
        @param cr: the database cursor
        @param uid: the user id
        @param ids: ids of stock move object to be scrapped
        @param quantity : specify scrap qty
        @param location_id : specify scrap location
        @param context: context arguments
        @return: Scraped lines
        """
        #quantity should be given in MOVE UOM
        if quantity <= 0:
            raise osv.except_osv(_('Warning!'), _('Please provide a positive quantity to scrap.'))
        res = []
        for move in self.browse(cr, uid, ids, context=context):
            source_location = move.location_id
            if move.state == 'done':
                source_location = move.location_dest_id
            #Previously used to prevent scraping from virtual location but not necessary anymore
            #if source_location.usage != 'internal':
                #restrict to scrap from a virtual location because it's meaningless and it may introduce errors in stock ('creating' new products from nowhere)
                #raise osv.except_osv(_('Error!'), _('Forbidden operation: it is not allowed to scrap products from a virtual location.'))
            if quantity > move.product_qty : continue
			
            move_qty = move.product_qty
            uos_qty = quantity / move_qty * move.product_uos_qty		

            pickint_type_code = move.picking_type_id.code or move.picking_id.picking_type_id.code	
            source_location = source_location.id
            dest_location = location_id				
            if pickint_type_code == 'outgoing':
                dest_location = move.location_dest_id.id
                source_location = location_id
				
            default_val = {
                'location_id': source_location,
                'product_uom_qty': quantity,
                'product_uos_qty': uos_qty,
                'state': move.state,
                'scrapped': False, #True,
                'location_dest_id': dest_location,
                'restrict_lot_id': restrict_lot_id,
                'restrict_partner_id': restrict_partner_id,
            }
            new_move = self.copy(cr, uid, move.id, default_val)
			
            actual_qty = move.product_uom_qty - quantity
            move.product_uos_qty = actual_qty
            move.product_uom_qty = actual_qty			
			
            res += [new_move]
            product_obj = self.pool.get('product.product')
            for product in product_obj.browse(cr, uid, [move.product_id.id], context=context):
                if move.picking_id:
                    uom = product.uom_id.name if product.uom_id else ''
                    message = _("%s %s %s has been <b>moved to</b> scrap.") % (quantity, uom, product.name)
                    move.picking_id.message_post(body=message)

        #self.action_done(cr, uid, res, context=context)
        return res			

	
class stock_picking(osv.osv):
    _inherit = "stock.picking"
    #_name = "stock.picking"

    def _get_final_hksz_amount(self, cr, uid, ids, field_names=None, arg=False, context=None):
	
        res = {}  	
        for pick in self.browse(cr, uid, ids, context=context):
            total = 0		
            for move in pick.move_lines:
                total += move.price_total_hksz			
            res[pick.id] = total
			
        return res		
	
    _columns = {
        'can_ship': fields.boolean(string="Inform shipping",default=False, copy=False),	
        'loc_id': fields.many2one('stock.location', 'Select Source'),
        'loc_dest_id': fields.many2one('stock.location', 'Select Destination'),	
        'so_reference':fields.related('sale_id','client_order_ref',type='char',string='SO Reference'),	
        'so_note':fields.related('sale_id','note',type='text',string='Sales Note'),	
        'final_hksz_amount': fields.function(_get_final_hksz_amount, type='float', string='Total Amount '),		
    }
			
	
    def do_unreserve_specified_lines(self, cr, uid, ids, context=None):
	
        quant_obj = self.pool.get("stock.quant")

        picking = self.browse(cr, uid, ids[0], context=context)		
        for move in picking.move_lines:
		
            if not move.is_checked : continue	
			
            if move.state in ('done', 'cancel'):
                raise osv.except_osv(_('Operation Forbidden!'), _('Cannot unreserve a done move'))
				
            quant_obj.quants_unreserve(cr, uid, move, context=context)
			
            ancestors = []
            move2 = move
            while move2:
                ancestors += [x.id for x in move2.move_orig_ids]
                move2 = not move2.move_orig_ids and move2.split_from or False
			
            if ancestors:
                move.write({'state': 'waiting', 'is_checked': False})
            else:
                move.write({'state': 'confirmed', 'is_checked': False})
				
    def inform_warehouse_shipping(self, cr, uid, ids, context=None ):
	
        for pick in self.browse(cr, uid, ids, context=context):

            if not ( pick.state in ['confirmed', 'partially_available','assigned'] ) :				
                continue
				
            if pick.can_ship == True:
                pick.can_ship = False	
            else:
                pick.can_ship = True
				
        return
		
    def change_location(self, cr, uid, ids, context=None ):
	
        for pick in self.browse(cr, uid, ids, context=context):
            for line in pick.move_lines:
                line.location_id = pick.loc_id
                line.location_dest_id = pick.loc_dest_id

        return		

    def set_to_draft(self, cr, uid, ids, context=None ):	
	
        for pick in self.browse(cr, uid, ids, context=context):
            if pick.state != 'cancel' : continue		
            for line in pick.move_lines:
                line.write({'state': 'draft'}, context=context)				
		
    def set_from_standby_location(self, cr, uid, ids, context=None ):
	
        for pick in self.browse(cr, uid, ids, context=context):
            for line in pick.move_lines:
                if line.name and line.name.find('RMA')>=0:			
                    line.location_id = 20 # Standby Location ID = 20

        return		
		
    def set_return_location(self, cr, uid, ids, context=None ):		

        src_id, dest_id = 9,20	#Customer Location id = 9 in default.
  		
        statement = """select id from stock_location where usage='internal' and name like '%sStandby' limit 1""" % '%'	
        cr.execute(statement)
        for i in cr.fetchall():
            dest_id = i[0]		
			
        for pick in self.browse(cr, uid, ids, context=context):
            pick.picking_type_id = 1	# Stock Reciepts ID = 1
            for line in pick.move_lines:
                line.location_dest_id = dest_id
                line.location_id = src_id				

        return        	
	
    def create(self, cr, user, vals, context=None):
        context = context or {}		
        id = super(stock_picking, self).create(cr, user, vals, context)	
        self.message_subscribe_users(cr, user, [id], user_ids=[5], context=context)	
        		
        return id	

    def add_followers(self, cr, uid, vals, context=None):	
        return self.message_subscribe_users(cr, uid, vals['ids'], user_ids=vals['user_ids'], context=context)  


    @api.cr_uid_ids_context
    def do_prepare_partial(self, cr, uid, picking_ids, context=None):
        context = context or {}
        pack_operation_obj = self.pool.get('stock.pack.operation')
        #used to avoid recomputing the remaining quantities at each new pack operation created
        ctx = context.copy()
        ctx['no_recompute'] = True

        #get list of existing operations and delete them
        existing_package_ids = pack_operation_obj.search(cr, uid, [('picking_id', 'in', picking_ids)], context=context)
        if existing_package_ids:
            pack_operation_obj.unlink(cr, uid, existing_package_ids, context)
        for picking in self.browse(cr, uid, picking_ids, context=context):
            forced_qties = {}  # Quantity remaining after calculating reserved quants
            picking_quants = []
			
            if picking.picking_type_id.code	== 'incoming':
                for move in picking.move_lines:		
                    if move.state not in ('assigned', 'confirmed'):
                        continue				
                    values = {'picking_id':picking.id, 'product_qty':move.product_uom_qty, 'product_id':move.product_id.id, 'location_id':move.location_id.id, 'location_dest_id':move.location_dest_id.id, 'product_uom_id':move.product_uom.id}						
                    pack_id = pack_operation_obj.create(cr, uid, values, context=ctx)							
			
                continue			
			
            #Calculate packages, reserved quants, qtys of this picking's moves
            for move in picking.move_lines:
                if move.state not in ('assigned', 'confirmed') or not move.reserved_availability :
                    continue
                					
                vals = {'picking_id':picking.id, 'product_qty':move.reserved_availability, 'product_id':move.product_id.id, 'location_id':move.location_id.id, 'location_dest_id':move.location_dest_id.id, 'product_uom_id':move.product_uom.id}	
                pack_operation_obj.create(cr, uid, vals, context=ctx)
                continue				
                #move_quants = move.reserved_quant_ids
                #picking_quants += move_quants
                #forced_qty = (move.state == 'assigned') and move.product_qty - sum([x.qty for x in move_quants]) or 0
				
                #if we used force_assign() on the move, or if the move is incoming, forced_qty > 0
                if float_compare(forced_qty, 0, precision_rounding=move.product_id.uom_id.rounding) > 0:
                    if forced_qties.get(move.product_id):
                        forced_qties[move.product_id] += forced_qty
                    else:
                        forced_qties[move.product_id] = forced_qty 
						
            #for vals in self._prepare_pack_ops(cr, uid, picking, picking_quants, forced_qties, context=context):
            #    pack_operation_obj.create(cr, uid, vals, context=ctx)
				
        #recompute the remaining quantities all at once
        self.do_recompute_remaining_quantities(cr, uid, picking_ids, context=context)
        self.write(cr, uid, picking_ids, {'recompute_pack_op': False}, context=context)	
		
	