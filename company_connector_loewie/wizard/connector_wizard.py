# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2010-2015 Elico Corp (<http://www.elico-corp.com>)
#    Authors: Xiaopeng Xie
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################

from openerp.osv import osv, fields
from openerp.tools.translate import _
import logging
import time

_logger = logging.getLogger(__name__)


class connector_wizard(osv.osv_memory):
    _name = 'connector.wizard'
    _description = 'Copy Data Wizard'

    def _get_company(self, cr, uid, context=None):
        company_obj = self.pool.get('res.company')
        ids = company_obj.search(cr, 1, [], context=context)
        res = []
        for company in company_obj.browse(cr, 1, ids, context=context):
            res.append(('%d' % company.id, company.name))
        return res

    _columns = {
        'src_company_id': fields.selection(_get_company, 'Source Company', required=True),
        'dest_company_id': fields.selection(_get_company, 'Destination Company', required=True),
        'src_order': fields.selection([('sale', 'Sale Order -> Purchase Order'), ('purchase', 'Purchase Order -> Sale Order')],'Source Order'),
        'dest_order': fields.selection([('sale', 'Sale Order'), ('purchase', 'Purchase Order')], 'Destination Order'),
        'src_orde_no': fields.char('Source Order NO'),
    }

    def apply(self, cr, uid, ids, context=None):
        ids = ids[0]
        wizard = self.browse(cr, uid, ids, context=context)
        src_company_id = wizard.src_company_id and int(wizard.src_company_id) or None
        dest_company_id = wizard.dest_company_id and int(wizard.dest_company_id) or None
        order_no = wizard.src_orde_no
        order_no = order_no or ''
        order_no = order_no.upper().strip()

        new_id = action = None
        if wizard.src_order == 'sale':
            new_id = self.sale2purchase(cr, uid, ids, src_company_id, dest_company_id,
                order_no, context=context)
            action = self.view_order(cr, uid, new_id, 'purchase.order', context=context)

        if wizard.src_order == 'purchase':
            new_id = self.purchase2sale(cr, uid, ids, src_company_id, dest_company_id,
                order_no, context=context)
            action = self.view_order(cr, uid, new_id, 'sale.order', context=context)

        return action

    def sale2purchase(self, cr, uid, ids, src_company_id, dest_company_id,
        order_no=None, context=None):
        sale_order_obj = self.pool.get('sale.order')
        purchase_order_obj = self.pool.get('purchase.order')
        purchase_order_line_obj = self.pool.get('purchase.order.line')

        domain = [('company_id', '=', src_company_id), ('name', '=', order_no)]
        order_ids = sale_order_obj.search(cr, 1, domain, limit=1, context=context)
        if not order_ids:
            raise osv.except_osv(_('Error!'), _("Oder doesn't exist!"))

        sale_order = sale_order_obj.browse(cr, 1, order_ids[0], context=context)
        location_id = 12
        partner_id = 6
        if dest_company_id == 1: # sz
            location_id = 20
            partner_id = 1929
        vals = {
            'company_id': dest_company_id,
            # 'currency_id': 8,
            # 'date_order': time.strftime('%Y-%m-%d %H:%M:%S'),
            'location_id': location_id,
            # 'picking_type_id': 1,
            'partner_id': partner_id,
            # 'journal_id': 35,
            'pricelist_id': sale_order.pricelist_id.id,
            # 'related_location_id': 12,
            'order_line': [],
        }

        context.update({'partner_id': partner_id})
        default_fields = ['currency_id', 'picking_type_id', 'journal_id', 'location_id', 'related_location_id']
        defaults = purchase_order_obj.default_get(cr, 1, default_fields, context=context)
        vals.update(defaults)

        for line in sale_order.order_line:
            order_line = [
                0,
                False,
                {
                    'name': line.name,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom.id,
                    'date_planned': time.strftime('%Y-%m-%d %H:%M:%S'),
                    'price_unit': line.price_unit,
                    'taxes_id': [[6, False, [x.id for x in line.tax_id]]],
                    'product_qty': line.product_uom_qty,
                    # 'account_analytic_id': x
                    # 'pur_currency_id': 3,
                }
            ]

            default_fields = ['price_unit', 'product_uom', 'product_qty', 'state']
            defaults = purchase_order_obj.default_get(cr, 1, default_fields, context=context)
            order_line[2].update(defaults)
            vals['order_line'].append(order_line)
        new_id = purchase_order_obj.create(cr, uid, vals, context=context)
        purchase_order = purchase_order_obj.browse(cr, uid, new_id, context=context)
        for line in purchase_order.order_line:
            vals = purchase_order_line_obj.onchange_product_id(
                cr, uid, line.id, purchase_order.pricelist_id.id,
                line.product_id.id, line.product_qty, line.product_uom.id,
                purchase_order.partner_id.id, date_order=False,
                fiscal_position_id=False,
                date_planned=False, name=line.name, price_unit=line.price_unit,
                state='draft', context=context)
            purchase_order_line_obj.write(cr, uid, line.id, vals['value'], context=context)
        return new_id

    def purchase2sale(self, cr, uid, ids, src_company_id, dest_company_id,
        order_no=None, context=None):
        sale_order_obj = self.pool.get('sale.order')
        sale_order_line_obj = self.pool.get('sale.order.line')
        purchase_order_obj = self.pool.get('purchase.order')
        domain = [('company_id', '=', src_company_id), ('name', '=', order_no)]
        order_ids = purchase_order_obj.search(cr, 1, domain, limit=1, context=context)
        if not order_ids:
            raise osv.except_osv(_('Error!'), _("Oder doesn't exist!"))

        purchase_order = purchase_order_obj.browse(
            cr, 1, order_ids[0], context=context)
        partner_id = 6
        if dest_company_id == 1: # sz
            partner_id = 1929
        vals = {
            'categ_ids': [[6, False, []]],
            'picking_policy': 'direct',
            'company_id': dest_company_id,
            'all_discounts': 0,
            'partner_id': partner_id,
            'pricelist_id': purchase_order.pricelist_id.id,
            # 'warehouse_id': 1,
            'order_line': [],
        }

        context.update({'partner_id': partner_id})
        default_fields = ['date_order', 'order_policy', 'state',
            'user_id', 'partner_invoice_id', 'partner_shipping_id', 'note',
            'section_id']
        defaults = purchase_order_obj.default_get(
            cr, 1, default_fields, context=context)
        vals.update(defaults)

        for line in purchase_order.order_line:
            name = line.name
            order_line = [
                0,
                False,
                {
                    'product_uos_qty': line.product_qty,
                    'product_id': line.product_id.id,
                    'product_uom': line.product_uom.id,
                    'sequence': '10',
                    'price_unit': line.price_unit,
                    'product_uom_qty': line.product_qty,
                    'name': name,
                    # 'product_tmpl_id': 5538,
                    # 'route_id': False,
                    # 'pur_price_unit': 22.5,
                    'delay': 7,
                    # 'address_allotment_id': False,
                    # 'th_weight': 0.22,
                    # 'product_uos': False,
                    'discount': 0,
                    'tax_id': [[6, False, [x.id for x in line.taxes_id]]],
                    # 'pur_currency_id': 1,
                    # 'product_packaging': False
                }
            ]
            vals['order_line'].append(order_line)
        new_id = sale_order_obj.create(cr, uid, vals, context=context)
        sale_order = sale_order_obj.browse(cr, uid, new_id, context=context)
        sale_order_obj.onchange_partner_id(
            cr, uid, new_id, sale_order.partner_id.id, context=context)
        for line in sale_order.order_line:
            vals = sale_order_line_obj.product_id_change(
                cr, uid, line.id, sale_order.pricelist_id.id,
                product=line.product_id.id, qty=line.product_uom_qty,
                uom=line.product_uom.id, qty_uos=line.product_uos_qty,
                uos=line.product_uos.id, name=line.name,
                partner_id=sale_order.partner_id.id,
                lang=False, update_tax=True, date_order=sale_order.date_order,
                packaging=False, fiscal_position=False, flag=False, context=context)
            sale_order_line_obj.write(cr, uid, line.id, vals['value'], context=context)
        return new_id

    def view_order(self, cr, uid, ids, model, context=None):
        url = None
        if model == 'sale.order':
            url = "web#id=%s&view_type=form&model=sale.order&action=405"% ids
        elif model == 'purchase.order':
            url = "web#id=%s&view_type=form&model=purchase.order&action=494"% ids

        return {'type': 'ir.actions.act_url', 'url': url, 'target': 'self'}
