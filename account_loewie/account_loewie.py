# -*- coding: utf-8 -*-
#from openerp.osv import osv
from openerp import models, fields, api, _
from datetime import datetime  # , timedelta
import openerp.addons.decimal_precision as dp

#from openerp.tools.translate import _
#_logger = logging.getLogger(__name__)

class purchase_order_line(models.Model):
    _inherit = "purchase.order.line"

    @api.one
    @api.depends('price_unit', 'product_qty')
    def _compute_subtotal_untaxed(self):	
        self.subtotal_untaxed = self.price_unit * self.product_qty		
	
    subtotal_untaxed = fields.Float(string=u'含税合计', digits=dp.get_precision('Account'), readonly=True, compute='_compute_subtotal_untaxed')


class sale_order_line(models.Model):
    _inherit = "sale.order.line"
    _order = 'id , order_id desc, sequence'
	
    @api.one
    @api.depends('price_unit','discount')
    def _compute_amount_hkd(self):
		
        amount = self.price_unit * self.product_uom_qty
        if self.discount : amount = amount * (100 - self.discount)/100	
		
        currency_from = self.order_id.pricelist_id.currency_id
        currency_to = 25 #  
        if currency_from.id == currency_to :
            self.amount_hkd = amount
            return
			
        date_confirm = self.order_id.date_confirm or self.order_id.date_order		
        date_confirm = datetime.strptime(date_confirm,"%Y-%m-%d")        			
        date_confirm = date_confirm.date()
        if date_confirm.year < 2016 :
            self.amount_hkd = amount		
            return	
		
        currency_rate_obj = self.env['res.currency.rate']
        so_cofirm_days = ( (date_confirm.year-2016) * 12 + date_confirm.month ) * 30 + date_confirm.day				
				
        tt = 20480		
        to_r = 1		
        to_rates = currency_rate_obj.search([('currency_id', '=', currency_to)])	#  order='write_date desc', 
        for rate in to_rates :
            rate_create_date = 	datetime.strptime(rate.create_date,"%Y-%m-%d %H:%M:%S").date()	
            rate_create_days = 	( (rate_create_date.year-2016) * 12 + rate_create_date.month ) * 30 + rate_create_date.day
            interval_days = so_cofirm_days - rate_create_days			
				
            if interval_days == 0:
                to_r = rate.rate		
                break
					
            if interval_days < 0:
                continue
					
            if tt > interval_days:
                to_r = rate.rate				
                tt = interval_days				

        tt = 20480			
        from_r = 1	
        for rate in currency_from.rate_ids:
            rate_create_date2 = datetime.strptime(rate.create_date,"%Y-%m-%d %H:%M:%S").date()			
            rate_create_days2 = ( (rate_create_date2.year-2016) * 12 + rate_create_date2.month ) * 30 + rate_create_date2.day
            interval_days = so_cofirm_days - rate_create_days2	
				
            if interval_days == 0:
                from_r = rate.rate		
                break
					
            if interval_days < 0:
                continue
					
            if tt > interval_days:
                from_r = rate.rate				
                tt = interval_days		
			
        #obj_precision = self.env['decimal.precision']
        #prec = obj_precision.precision_get('Account')			

        self.amount_hkd = round(( to_r / from_r )*amount, 2) # prec)
		
    @api.one
    @api.depends('price_unit', 'discount')
    def _compute_price_discounted(self):
	
        if self.discount >= 100 or self.discount <= 0 :
            self.price_discounted = self.price_unit		
        else: 
            self.price_discounted = self.price_unit * (100 - self.discount)	/ 100
	
    price_discounted = fields.Float(string=u'折后单价', digits=dp.get_precision('Account'), readonly=True, compute='_compute_price_discounted')
    amount_hkd = fields.Float(compute='_compute_amount_hkd', readonly=True, string='Subtotal(HKD)')	
    #amount_tax = fields.Float(string='Tax', digits=dp.get_precision('Account'),
    #    store=True, readonly=True, compute='_compute_amount')
	
class sale_order(models.Model):
    _inherit = "sale.order"	
	
    @api.one
    @api.depends('amount_total','date_confirm')
    def _compute_amount_hkd(self):
		
        amount = self.amount_total
        currency_from = self.pricelist_id.currency_id
        currency_to = 25 # hkd 25   self.pool.get('res.currency').search(cr,uid,) 
        if currency_from.id == currency_to :
            self.amount_hkd = amount
            return
 
        if not self.date_confirm:
            date_confirm = datetime.strptime(self.create_date,"%Y-%m-%d %H:%M:%S")		
            date_confirm = date_confirm.date()		
        else:			
            date_confirm = datetime.strptime(self.date_confirm,"%Y-%m-%d")        			
            date_confirm = date_confirm.date()
			
        if date_confirm.year < 2016 :
            self.amount_hkd = amount		
            return	
		
        currency_rate_obj = self.env['res.currency.rate']
        so_cofirm_days = ( (date_confirm.year-2016) * 12 + date_confirm.month ) * 30 + date_confirm.day				
				
        tt = 20480		
        interval_days = 20480
        to_r = 1		
        to_rates = currency_rate_obj.search([('currency_id', '=', currency_to)])	#  order='write_date desc', 
        for rate in to_rates :
            rate_create_date = 	datetime.strptime(rate.create_date,"%Y-%m-%d %H:%M:%S").date()	
            rate_create_days = 	( (rate_create_date.year-2016) * 12 + rate_create_date.month ) * 30 + rate_create_date.day
            interval_days = so_cofirm_days - rate_create_days			
				
            if interval_days == 0:
                to_r = rate.rate		
                break
					
            if interval_days < 0:
                continue
					
            if tt > interval_days:
                to_r = rate.rate				
                tt = interval_days				

        tt = 20480	
        interval_days = 20480		
        from_r = 1	
        for rate in currency_from.rate_ids:
            rate_create_date2 = 	datetime.strptime(rate.create_date,"%Y-%m-%d %H:%M:%S").date()			
            rate_create_days2 = ( (rate_create_date2.year-2016) * 12 + rate_create_date2.month ) * 30 + rate_create_date2.day
            interval_days = so_cofirm_days - rate_create_days2	
				
            if interval_days == 0:
                from_r = rate.rate		
                break
					
            if interval_days < 0:
                continue
					
            if tt > interval_days:
                from_r = rate.rate				
                tt = interval_days		
			
        #obj_precision = self.env['decimal.precision']
        #prec = obj_precision.precision_get('Account')			

        self.amount_hkd = round(( to_r / from_r )*amount, 2) # prec)
			
    sales_team = fields.Many2one('crm.case.section', string=u'销售分组', related='partner_id.section_id', store=True, readonly=True)
    amount_hkd = fields.Float(compute='_compute_amount_hkd', readonly=True, string='Amount HKD')	

    def loewie_invoice_create(self, cr, uid, ids, context=None):

        res = False
        invoices = {}
        invoice_ids = []
        invoice = self.pool.get('account.invoice')
        obj_sale_order_line = self.pool.get('sale.order.line')

        for o in self.browse(cr, uid, ids, context=context):
            cr.execute("select id from sale_order_line where order_id=%d" % o.id)
            lines = [ item[0] for item in cr.fetchall()]
            created_lines = obj_sale_order_line.invoice_line_create(cr, uid, lines)
            if created_lines:
                invoices.setdefault(o.partner_invoice_id.id or o.partner_id.id, []).append((o, created_lines))

        for val in invoices.values():
            for order, il in val:
                res = self._make_invoice(cr, uid, order, il, context=context)
                invoice_ids.append(res)
                self.write(cr, uid, [order.id], {'state': 'progress'})
                cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (order.id, res))
                self.invalidate_cache(cr, uid, ['invoice_ids'], [order.id], context=context)
				
        return res
    """  	
    def loewie_manual_invoice(self, cr, uid, ids, context=None):
        create invoices for the given sales orders (ids), and open the form
            view of one of the newly created invoices

        mod_obj = self.pool.get('ir.model.data')
        
        # create invoices through the sales orders' workflow
        inv_ids0 = set(inv.id for sale in self.browse(cr, uid, ids, context) for inv in sale.invoice_ids)
        self.signal_workflow(cr, uid, ids, 'manual_invoice')
        inv_ids1 = set(inv.id for sale in self.browse(cr, uid, ids, context) for inv in sale.invoice_ids)
        # determine newly created invoices
        new_inv_ids = list(inv_ids1 - inv_ids0)

        res = mod_obj.get_object_reference(cr, uid, 'account', 'invoice_form')
        res_id = res and res[1] or False,

        return {
            'name': _('Customer Invoices'),
            'view_type': 'form',
            'view_mode': 'form',
            'view_id': [res_id],
            'res_model': 'account.invoice',
            'context': "{'type':'out_invoice'}",
            'type': 'ir.actions.act_window',
            'nodestroy': True,
            'target': 'current',
            'res_id': new_inv_ids and new_inv_ids[0] or False,
        }	
    """		
    def _prepare_invoice(self, cr, uid, order, lines, context=None):
        """Prepare the dict of values to create the new invoice for a
           sales order. This method may be overridden to implement custom
           invoice generation (making sure to call super() to establish
           a clean extension chain).

           :param browse_record order: sale.order record to invoice
           :param list(int) line: list of invoice line IDs that must be
                                  attached to the invoice
           :return: dict of value to create() the invoice
        """
        # if not order.return_pick and order.amount_total < 0 : return {}  # 小于 0 一般为冲减销售单，  
		
        if context is None:
            context = {}
        journal_ids = self.pool.get('account.journal').search(cr, uid,
            [('type', '=', 'sale'), ('company_id', '=', order.company_id.id)],
            limit=1)
        if not journal_ids:
            raise osv.except_osv(_('Error!'),
                _('Please define sales journal for this company: "%s" (id:%d).') % (order.company_id.name, order.company_id.id))
        invoice_vals = {
            'name': order.client_order_ref or '',
            'origin': order.name,
            'sale_id': order.id,
            #'picking_id': order.name,			
            'type': 'out_invoice',
            'reference': order.client_order_ref or order.name,
            'account_id': order.partner_id.property_account_receivable.id,
            'partner_id': order.partner_invoice_id.id,
            'journal_id': journal_ids[0],
            'invoice_line': [(6, 0, lines)],
            'currency_id': order.pricelist_id.currency_id.id,
            'comment': order.note,
            'payment_term': order.payment_term and order.payment_term.id or False,
            'fiscal_position': order.fiscal_position.id or order.partner_id.property_account_position.id,
            'date_invoice': context.get('date_invoice', False),
            'company_id': order.company_id.id,
            'user_id': order.user_id and order.user_id.id or False,
            'section_id' : order.section_id.id
        }
 
        # Care for deprecated _inv_get() hook - FIXME: to be removed after 6.1
        invoice_vals.update(self._inv_get(cr, uid, order, context=context))
        if order.return_pick : 	invoice_vals.update({'picking_id':order.return_pick.id})		
        return invoice_vals

    """	
    def action_invoice_create(self, cr, uid, ids, grouped=False, states=None, date_invoice = False, context=None):
        if states is None:
            states = ['confirmed', 'done', 'exception']
        res = False
        invoices = {}
        invoice_ids = []
        invoice = self.pool.get('account.invoice')
        obj_sale_order_line = self.pool.get('sale.order.line')
        partner_currency = {}
        # If date was specified, use it as date invoiced, usefull when invoices are generated this month and put the
        # last day of the last month as invoice date
        if date_invoice:
            context = dict(context or {}, date_invoice=date_invoice)
        for o in self.browse(cr, uid, ids, context=context):
            currency_id = o.pricelist_id.currency_id.id
            if (o.partner_id.id in partner_currency) and (partner_currency[o.partner_id.id] <> currency_id):
                raise osv.except_osv(
                    _('Error!'),
                    _('You cannot group sales having different currencies for the same partner.'))

            partner_currency[o.partner_id.id] = currency_id
            lines = []
            for line in o.order_line:
                if line.invoiced:
                    continue
                elif (line.state in states):
                    lines.append(line.id)
            created_lines = obj_sale_order_line.invoice_line_create(cr, uid, lines)
            if created_lines:
                invoices.setdefault(o.partner_invoice_id.id or o.partner_id.id, []).append((o, created_lines))
        if not invoices:
            for o in self.browse(cr, uid, ids, context=context):
                for i in o.invoice_ids:
                    if i.state == 'draft':
                        return i.id
        for val in invoices.values():
            if grouped:
                res = self._make_invoice(cr, uid, val[0][0], reduce(lambda x, y: x + y, [l for o, l in val], []), context=context)
                invoice_ref = ''
                origin_ref = ''
                for o, l in val:
                    invoice_ref += (o.client_order_ref or o.name) + '|'
                    origin_ref += (o.origin or o.name) + '|'
                    self.write(cr, uid, [o.id], {'state': 'progress'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (o.id, res))
                    self.invalidate_cache(cr, uid, ['invoice_ids'], [o.id], context=context)
                #remove last '|' in invoice_ref
                if len(invoice_ref) >= 1:
                    invoice_ref = invoice_ref[:-1]
                if len(origin_ref) >= 1:
                    origin_ref = origin_ref[:-1]
                invoice.write(cr, uid, [res], {'origin': origin_ref, 'name': invoice_ref, 'sale_id':, 'picking_id':})
            else:
                for order, il in val:
                    res = self._make_invoice(cr, uid, order, il, context=context)
                    invoice_ids.append(res)
                    self.write(cr, uid, [order.id], {'state': 'progress'})
                    cr.execute('insert into sale_order_invoice_rel (order_id,invoice_id) values (%s,%s)', (order.id, res))
                    self.invalidate_cache(cr, uid, ['invoice_ids'], [order.id], context=context)
        return res
        """

		
class account_invoice(models.Model):
    _inherit = ['account.invoice']
    _order = "id desc, number desc"
    """	
    @api.model
    def _default_sales_order(self):
        inv_type = self._context.get('type', 'out_invoice')
        inv_types = inv_type if isinstance(inv_type, list) else [inv_type]
        company_id = self._context.get('company_id', self.env.user.company_id.id)
        domain = [
            ('type', 'in', filter(None, map(TYPE2JOURNAL.get, inv_types))),
            ('company_id', '=', company_id),
        ] 已做红字发票
        return self.env['account.journal'].search(domain, limit=1)	"""
		
    date_done = fields.Datetime(related='picking_id.date_done',string=u'发货日期')	
    sale_id = fields.Many2one('sale.order', string='Sales Order', readonly=True, states={'draft': [('readonly', False)]})
        #default=_default_sales_order)	
		
    picking_id = fields.Many2one('stock.picking', string='Stock Picking', readonly=True, states={'draft': [('readonly', False)]})
        #default=_default_sales_order)	

    purchase_id = fields.Many2one('purchase.order', string='Purchase Order', readonly=True, states={'draft': [('readonly', False)]})
        #default=_default_sales_order)		
		
    def back_write_picks_ref_invoice(self, cr, uid, ids, context=None):
        invoice_obj = self.pool.get('account.invoice')
        invoices = invoice_obj.search(cr,uid,[],context=context)
        objs = invoice_obj.browse(cr,uid,invoices,context=context)
        for obj in objs:
            if not obj.picking_id : continue		
            #obj.picking_id.ref_invoice = obj.id
            obj.write({'date_invoice':obj.date_done,'date_due':obj.date_done})			
		
		

