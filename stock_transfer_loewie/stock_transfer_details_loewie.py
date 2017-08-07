# -*- coding: utf-8 -*-
from openerp import models, fields, api
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp
from datetime import datetime

class stock_transfer_details_loewie(models.TransientModel):
    _inherit = 'stock.transfer_details'
    _description = 'Picking wizard'

    picking_id = fields.Many2one('stock.picking', 'Picking')
    default_package = fields.Many2one('stock.quant.package', 'Default Package') 
    new_pack_name = fields.Char('New Pack Name')	
    check_num = fields.Char('Check Index:')	
    package_weight = fields.Float('Weight')	
    ul_id = fields.Many2one('product.ul','Specification')
    item_ids = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Items', domain=[('product_id', '!=', False)])
    item_ids_packed = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Packed', domain=['&',('product_id', '!=', False),('packed','=',True)])
    item_ids_unpacked = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Unpacked', domain=['&',('product_id', '!=', False),('packed','=',False)])	
    packop_ids = fields.One2many('stock.transfer_details_items', 'transfer_id', 'Packs', domain=[('product_id', '=', False)])
    picking_source_location_id = fields.Many2one('stock.location', string="Head source location", related='picking_id.location_id', store=False, readonly=True)
    picking_destination_location_id = fields.Many2one('stock.location', string="Head destination location", related='picking_id.location_dest_id', store=False, readonly=True)

    def default_get(self, cr, uid, fields, context=None):
        if context is None: context = {}
        res = super(stock_transfer_details_loewie, self).default_get(cr, uid, fields, context=context)
        picking_ids = context.get('active_ids', [])
        active_model = context.get('active_model')

        if not picking_ids or len(picking_ids) != 1:
            # Partial Picking Processing may only be done for one picking at a time
            return res
        assert active_model in ('stock.picking'), 'Bad context propagation'
        picking_id, = picking_ids
        picking = self.pool.get('stock.picking').browse(cr, uid, picking_id, context=context)
        items = []
        packs = []
        if not picking.pack_operation_ids:
            picking.do_prepare_partial()
        for op in picking.pack_operation_ids:
            item = {
                'packop_id': op.id,
                'product_id': op.product_id.id,
                'product_uom_id': op.product_uom_id.id,
                'quantity': op.product_qty,
                'package_id': op.package_id.id,
                'lot_id': op.lot_id.id,
                'sourceloc_id': op.location_id.id,
                'destinationloc_id': op.location_dest_id.id,
                'result_package_id': op.result_package_id.id,
                'date': op.date, 
                'owner_id': op.owner_id.id,
            }
            if op.product_id:
                items.append(item)
            elif op.package_id:
                packs.append(item)
        res.update(item_ids=items)
        res.update(packop_ids=packs)
        return res

    @api.one
    def do_detailed_transfer(self):
        processed_ids = []
        # Create new and update existing pack operations
        for lstits in [self.item_ids, self.packop_ids]:
            for prod in lstits:
                pack_datas = {
                    'product_id': prod.product_id.id,
                    'product_uom_id': prod.product_uom_id.id,
                    'product_qty': prod.quantity,
                    'package_id': prod.package_id.id,
                    'lot_id': prod.lot_id.id,
                    'location_id': prod.sourceloc_id.id,
                    'location_dest_id': prod.destinationloc_id.id,
                    'result_package_id': prod.result_package_id.id,
                    'date': prod.date if prod.date else datetime.now(),
                    'owner_id': prod.owner_id.id,
                }
                if prod.packop_id:
                    prod.packop_id.write(pack_datas)
                    processed_ids.append(prod.packop_id.id)
                else:
                    pack_datas['picking_id'] = self.picking_id.id
                    packop_id = self.env['stock.pack.operation'].create(pack_datas)
                    processed_ids.append(packop_id.id)
        # Delete the others
        packops = self.env['stock.pack.operation'].search(['&', ('picking_id', '=', self.picking_id.id), '!', ('id', 'in', processed_ids)])
        for packop in packops:
            packop.unlink()

        # Execute the transfer of the picking
        self.picking_id.do_transfer()

        return True
		
		#
    def compute_products_qty(self,move_lines=None,op_lines=None,calc=False):
 
        move_product_ids = {}
        op_product_ids = {}
		
        if move_lines:		
            for line in move_lines:
                if line.product_id not in move_product_ids:			
                    move_product_ids[line.product_id] = line.reserved_availability #line.product_uom_qty
                else:
                    move_product_ids[line.product_id] += line.reserved_availability #line.product_uom_qty    
            if not calc:
                return move_product_ids			

        if op_lines:		
            for line in op_lines:
                if line.product_id not in op_product_ids:			
                    op_product_ids[line.product_id] = line.quantity
                else:
                    op_product_ids[line.product_id] = line.quantity + op_product_ids[line.product_id]
              
        if calc:				
            for key in op_product_ids.keys():  # calculate the unpack product quantity		
                if move_product_ids[key]  > op_product_ids[key]:		
                    op_product_ids[key] = move_product_ids[key] - op_product_ids[key]
                else:
                    del(op_product_ids[key])				
				
        return op_product_ids					
		
    @api.multi
    def set_packno(self):
		
        for packop in self.item_ids:
            if packop.check	:	
                packop.result_package_id = self.default_package
                packop.check = False
                packop.packed = True				
	
        product_ids = self.compute_products_qty(self.picking_id.move_lines,self.item_ids,True)
        
		#create operation lines which remained
        for key in product_ids:
             for packop in self.item_ids:
                if key == packop.product_id : 
                    newop = packop.copy(context=self.env.context)
                    newop.quantity = product_ids[key]
                    newop.packop_id = False
                    newop.result_package_id = False	
                    newop.packed = False					
                    break					
		
        return self.wizard_view() 

    @api.multi		
    def check_all_unpacked_products(self):
        num = int(self.check_num)
        if num == 0:	
            for item in self.item_ids_unpacked:
                item.check = True
				
        if num == -1:
            for item in self.item_ids_unpacked:
                item.check = False

        if num > 0 and num < len(self.items_ids_unpaced):

            for item in self.items_ids_unpaced:
                item.check = True
                num -= 1
                if num < 1: break				
				
        return self.wizard_view()  
		
    @api.multi
    def create_pack(self):
        packages = self.pool.get('stock.quant.package')
        newpack = packages.search(self._cr, self._uid,[('name','=',self.new_pack_name)],context=self._context)
		
        if not newpack: 
            newpack = packages.create(self._cr, self._uid, {'name':self.new_pack_name,'package_weight':self.package_weight,'ul_id':self.ul_id.id}, self._context)    	
        
        return self.wizard_view() 	
		
    @api.multi
    def wizard_view(self):
        view = self.env.ref('stock_transfer_loewie.view_stock_transfer_loewie')
		
        """		
        for transfer in self.item_ids:		
            if transfer.packop_id and transfer.packop_id.linked_move_operation_ids:		
                transfer.destinationloc_id = transfer.packop_id.linked_move_operation_ids[0].move_id.location_dest_id.id
                transfer.sourceloc_id = transfer.packop_id.linked_move_operation_ids[0].move_id.location_id.id	
				
                transfer.packop_id.location_dest_id = transfer.packop_id.linked_move_operation_ids[0].move_id.location_dest_id.id			
                transfer.packop_id.location_id = transfer.packop_id.linked_move_operation_ids[0].move_id.location_id.id	

        for transfer in self.packop_ids: 				
            if transfer.packop_id and transfer.packop_id.linked_move_operation_ids:						
                transfer.packop_id.location_dest_id = transfer.packop_id.linked_move_operation_ids[0].move_id.location_dest_id.id			
                transfer.packop_id.location_id = transfer.packop_id.linked_move_operation_ids[0].move_id.location_id.id
        """				
		
        return {
            'name': _('Enter transfer details'),
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'stock.transfer_details',
            'views': [(view.id, 'form')],
            'view_id': view.id,
            'target': 'new',
            'res_id': self.ids[0],
            'context': self.env.context,
        }


class stock_transfer_details_items_loewie(models.TransientModel):
    _inherit = 'stock.transfer_details_items'
    _description = 'Picking wizard items'

    transfer_id = fields.Many2one('stock.transfer_details', 'Transfer')
    check = fields.Boolean('Check')
    packed = fields.Boolean('Packed')
    packop_id = fields.Many2one('stock.pack.operation', 'Operation')
    product_id = fields.Many2one('product.product', 'Product')
    product_uom_id = fields.Many2one('product.uom', 'Product Unit of Measure')
    quantity = fields.Float('Quantity', digits=dp.get_precision('Product Unit of Measure'), default = 1.0)
    package_id = fields.Many2one('stock.quant.package', 'Source package', domain="['|', ('location_id', 'child_of', sourceloc_id), ('location_id','=',False)]")
    lot_id = fields.Many2one('stock.production.lot', 'Lot/Serial Number')
    sourceloc_id = fields.Many2one('stock.location', 'Source Location', required=True)
    destinationloc_id = fields.Many2one('stock.location', 'Destination Location', required=True)
    result_package_id = fields.Many2one('stock.quant.package', 'Destination package', domain="['|', ('location_id', 'child_of', destinationloc_id), ('location_id','=',False)]")
    date = fields.Datetime('Date')
    owner_id = fields.Many2one('res.partner', 'Owner', help="Owner of the quants")

    @api.multi
    def split_quantities(self):
        for det in self:
            if det.quantity>1:
                tmp_num = det.quantity			
                det.quantity = int(det.quantity/2)
                new_id = det.copy(context=self.env.context)
                new_id.quantity = int(tmp_num - det.quantity)
                new_id.packop_id = False
        if self and self[0]:
            return self[0].transfer_id.wizard_view()

    @api.multi
    def put_in_pack(self):
        newpack = None
        for packop in self:
            if not packop.result_package_id:
                if not newpack:
                    newpack = self.pool['stock.quant.package'].create(self._cr, self._uid, {'location_id': packop.destinationloc_id.id if packop.destinationloc_id else False}, self._context)
                packop.result_package_id = newpack
        if self and self[0]:
            return self[0].transfer_id.wizard_view()	
			
    @api.multi
    def product_id_change(self, product, uom=False):
        result = {}
        if product:
            prod = self.env['product.product'].browse(product)
            result['product_uom_id'] = prod.uom_id and prod.uom_id.id
            return {'value': result, 'domain': {}, 'warning':{} }

    @api.multi
    def source_package_change(self, sourcepackage):			
        result = {}
        if sourcepackage:
            pack = self.env['stock.quant.package'].browse(sourcepackage)
            result['sourceloc_id'] = pack.location_id and pack.location_id.id
            return {'value': result, 'domain': {}, 'warning':{} }
