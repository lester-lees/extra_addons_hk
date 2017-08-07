# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp.tools.translate import _
import openerp.addons.decimal_precision as dp

import logging

_logger = logging.getLogger(__name__)


class purchase_order_line(osv.osv):
    _inherit = 'purchase.order.line'

    def _pur_amount_line(self, cr, uid, ids, prop, arg, context=None):
        res = {}
        cur_obj = self.pool.get('res.currency')
        tax_obj = self.pool.get('account.tax')
        line_obj = self.pool.get('purchase.order.line')
        for line in line_obj.browse(cr, uid, ids, context=context):
            res[line.id] = {
                # 'price_subtotal': 0.0,
                'pur_price_unit': 0.0,
                'pur_price_subtotal': 0.0,
            }
            taxes = tax_obj.compute_all(
                cr, uid, line.taxes_id, line.price_unit, line.product_qty,
                line.product_id, line.order_id.partner_id)
            cur = line.order_id.pricelist_id.currency_id
            # LY
            subtotal = cur_obj.round(cr, uid, cur, taxes['total'])
            # res[line.id]['price_subtotal'] = subtotal

            pur_cur_id = line.pur_currency_id

            if line.order_id.pricelist_id.use_purchase_currency:			
                pur_price_unit = cur_obj.compute(cr, uid, cur.id, pur_cur_id.id, line.price_unit, context=context)
                pur_price_subtotal = cur_obj.compute(cr, uid, cur.id, pur_cur_id.id, subtotal, context=context)
            else:
                pur_price_unit = line.price_unit
                pur_price_subtotal = line.price_subtotal
				
            res[line.id]['pur_price_unit'] = pur_price_unit			
            res[line.id]['pur_price_subtotal'] = pur_price_subtotal
        return res

    _columns = {
        'pur_currency_id': fields.many2one('res.currency', 'Pur Currency'),
        # LY separate from original fields function
        # 'price_subtotal': fields.function(
        #     _amount_line, string='Subtotal',
        #     digits_compute= dp.get_precision('Account'),
        #     store={
        #         'purchase.order.line': (lambda self, cr, uid, ids, c={}: ids, ['product_id','price_unit'], 5),
        #     },
        #     multi='purchase'),
        'pur_price_unit': fields.function(
            _pur_amount_line, string='Pur Price Unit',
            digits_compute=dp.get_precision('Account'),
            store={
                'purchase.order.line': (
                    lambda self, cr, uid, ids, c={}: ids, ['product_id', 'price_unit'], 10),
            },
            multi='purchase'),
        'pur_price_subtotal': fields.function(
            _pur_amount_line, string='Pur Subtotal',
            digits_compute=dp.get_precision('Account'),
            store={
                'purchase.order.line': (
                    lambda self, cr, uid, ids, c={}: ids, ['product_id', 'price_unit'], 10),
            },
            multi='purchase'),
        'sequence': fields.integer(
            'Sequence',
            help="""Gives the sequence order when displaying 
            a list of purchase order lines."""),

    }

    _defaults = {
        'sequence': 10,
    }

    def onchange_product_id(self, cr, uid, ids, pricelist_id, product_id, qty,
        uom_id, partner_id, date_order=False, fiscal_position_id=False,
        date_planned=False, name=False, price_unit=False, state='draft', context=None):
        # LY mock super
        res = super(purchase_order_line, self).onchange_product_id(
            cr, uid, ids, pricelist_id, product_id, qty, uom_id,
            partner_id, date_order, fiscal_position_id, date_planned,
            name, price_unit, state, context)

        res = self.update_price_based_on_purchase_currency(
            cr, uid, res, pricelist_id, product_id, context)
        return res
		
    def get_purchase_price(self, cr, pricelist_id=None, product_id=None):
	
        if (not pricelist_id) or (not product_id):
            return 0		
			
        cr.execute("select price_surcharge from product_pricelist_item where product_id = %d and price_version_id = ( select id from product_pricelist_version where pricelist_id=%d limit 1)" % (product_id,pricelist_id) )
        price = 0		
        for res in cr.fetchall():
            price = res[0]

        return price			

    def update_price_based_on_purchase_currency(
        self, cr, uid, value, pricelist_id, product_id, context):
        if not product_id or not pricelist_id:
            return

        pricelist_data_obj = self.pool.get('product.pricelist').browse(
            cr, uid, [pricelist_id], context=context)[0]
        # not in purchase currency condition.
        #if not pricelist_data_obj.use_purchase_currency:
        #    return value

        # get price_unit
        original_price = value.get('value', {}).get('price_unit', -1)
		
		#Jimmy add 2016-01-21 11:27
        if original_price == 0:
            original_price = self.get_purchase_price(cr, pricelist_id, product_id)		 
        # update price based on purchase_invoice_currency
        # get invoice currency

        invoice_currency_id = pricelist_data_obj.currency_id.id

        # get purchase currency
        product_pool = self.pool.get('product.product')
        product_obj = product_pool.browse(cr, uid, product_id, context=context)
        purchase_curr_id = product_obj.purchase_currency_id.id

        warning_msgs = ""
        if not purchase_curr_id:
            # no set purchase currency.
            # todo raise warning
            warn_msg = _("""Product Purchase Curreny is not configured yet.\n"
               "use company currency \n.""")
            warning_msgs += _("No valid product purchase currency found !:") + \
                warn_msg + "\n\n"
            purchase_curr_id = product_obj.company_id.currency_id.id

        currency_obj = self.pool.get('res.currency')

        if pricelist_data_obj.use_purchase_currency and purchase_curr_id != invoice_currency_id:		
            original_price = currency_obj.compute(cr, uid, purchase_curr_id, invoice_currency_id, original_price, context=context)
			
        product_name = '.'
        if product_obj.description_sale:
            product_name += product_obj.description_sale
			
        # update price unit & currency
        to_update_vals = {
            'price_unit': original_price,
            'pur_currency_id': purchase_curr_id,
            'name': product_name,			
        }

        # update
        value.get('value', {}).update(to_update_vals)
        #if warning_msgs:
        #    warning = value.get('warning', {})
        #    old_warning_msgs = warning.get('message', '')
        #    warning.update({'message': old_warning_msgs + warning_msgs})
        #    value.update({'warning': warning})

        return value