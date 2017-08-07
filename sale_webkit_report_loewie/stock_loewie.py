# -*- coding: utf-8 -*-
from openerp.osv import fields, osv
from openerp import tools
import base64
import datetime
from openerp.addons.base.ir.ir_mail_server import MailDeliveryException
import logging
_logger = logging.getLogger(__name__)

class mail_mail(osv.Model):

    _inherit = 'mail.mail'
	

    def send(self, cr, uid, ids, bcc=False, auto_commit=False, raise_exception=False, context=None):
        context = dict(context or {})
        ir_mail_server = self.pool.get('ir.mail_server')
        ir_attachment = self.pool['ir.attachment']
        for mail in self.browse(cr, 1, ids, context=context):
            try:
                if mail.model:
                    model_id = self.pool['ir.model'].search(cr, 1, [('model', '=', mail.model)], context=context)[0]
                    model = self.pool['ir.model'].browse(cr, 1, model_id, context=context)
                else:
                    model = None
                if model:
                    context['model_name'] = model.name

                attachment_ids = [a.id for a in mail.attachment_ids]
                attachments = [(a['datas_fname'], base64.b64decode(a['datas']))
                                 for a in ir_attachment.read(cr, 1, attachment_ids,
                                                             ['datas_fname', 'datas'])]

                email_list = []
                if mail.email_to:
                    email_list.append(self.send_get_email_dict(cr, uid, mail, context=context))
                for partner in mail.recipient_ids:
                    email_list.append(self.send_get_email_dict(cr, uid, mail, partner=partner, context=context))
                # headers
                headers = {}
                bounce_alias = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.bounce.alias", context=context)
                catchall_domain = self.pool['ir.config_parameter'].get_param(cr, uid, "mail.catchall.domain", context=context)
                if bounce_alias and catchall_domain:
                    if mail.model and mail.res_id:
                        headers['Return-Path'] = '%s-%d-%s-%d@%s' % (bounce_alias, mail.id, mail.model, mail.res_id, catchall_domain)
                    else:
                        headers['Return-Path'] = '%s-%d@%s' % (bounce_alias, mail.id, catchall_domain)
                if mail.headers:
                    try:
                        headers.update(eval(mail.headers))
                    except Exception:
                        pass

                mail.write({'state': 'exception'})
                mail_sent = False

                res = None
                for email in email_list:
                    msg = ir_mail_server.build_email(
                        email_from=mail.email_from,
                        email_to=email.get('email_to'),
                        subject=email.get('subject'),
                        body=email.get('body'),
                        body_alternative=email.get('body_alternative'),
                        email_cc=tools.email_split(mail.email_cc),
                        email_bcc=tools.email_split(bcc),						
                        reply_to=mail.reply_to,
                        attachments=attachments,
                        message_id=mail.message_id,
                        references=mail.references,
                        object_id=mail.res_id and ('%s-%s' % (mail.res_id, mail.model)),
                        subtype='html',
                        subtype_alternative='plain',
                        headers=headers)
                    try:
                        res = ir_mail_server.send_email(cr, uid, msg,
                                                    mail_server_id=mail.mail_server_id.id,
                                                    context=context)
                    except AssertionError as error:
                        if error.message == ir_mail_server.NO_VALID_RECIPIENT:
                            _logger.warning("Ignoring invalid recipients for mail.mail %s: %s",
                                            mail.message_id, email.get('email_to'))
                        else:
                            raise
                if res:
                    mail.write({'state': 'sent', 'message_id': res})
                    mail_sent = True

                if mail_sent:
                    _logger.info('Mail with ID %r and Message-Id %r successfully sent', mail.id, mail.message_id)
                self._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=mail_sent)
            except MemoryError:
                _logger.exception('MemoryError while processing mail with ID %r and Msg-Id %r. '\
                                      'Consider raising the --limit-memory-hard startup option',
                                  mail.id, mail.message_id)
                raise
            except Exception as e:
                _logger.exception('failed sending mail.mail %s', mail.id)
                mail.write({'state': 'exception'})
                self._postprocess_sent_message(cr, uid, mail, context=context, mail_sent=False)
                if raise_exception:
                    if isinstance(e, AssertionError):
                        value = '. '.join(e.args)
                        raise MailDeliveryException(_("Mail Delivery Failed"), value)
                    raise

            if auto_commit is True:
                cr.commit()
        return True
    """		
    """

class stock_picking(osv.osv):
    _inherit = "stock.picking"
	
    _columns = {
        'delaration': fields.text(string="Express Delaration", default=u'"Lithium Ion Batteries in compliance with Section II of PI967"'),	
        #'pricelist_id': fields.many2one('product.pricelist', 'Price List'),		
    }		

    def create_saleorder_from_picking(self, cr, uid, ids, context=None ):		
        sale_order_obj = self.pool.get('sale.order')
        sale_order_line_obj = self.pool.get('sale.order.line')
		
        this = self.browse(cr, uid, ids, context=context)[0]		

        vals = {
            'client_order_ref': u'Template Quotation',		
            'picking_policy': 'direct',
            'order_policy': 'manual',			
            'company_id': this.company_id.id,
            'all_discounts': 0,
            'partner_id': this.partner_id.id,
            'pricelist_id': 22, # this.sale_id.pricelist_id.id,
            'warehouse_id': 1, # this.picking_type_id.warehouse_id.id,
            'user_id': this.sale_id.user_id.id or this.create_uid.id, 
            'state':'draft',
            'partner_invoice_id': this.partner_id.id, # this.sale_id.partner_invoice_id.id,
            'partner_shipping_id': this.partner_id.id, # this.sale_id.partner_shipping_id.id,			
            'date_order': datetime.datetime.now(),	
            #'return_pick':ids[0],			
        }
			
        new_id = sale_order_obj.create(cr, uid, vals, context=context)
        sale_order = sale_order_obj.browse(cr, uid, new_id, context=context)
        sale_order_obj.onchange_partner_id(
            cr, uid, new_id, sale_order.partner_id.id, context=context)		
        sale_order_name = sale_order.name		
		
        for line in this.move_lines:		
            order_line = {
                'order_id': new_id,				
                'product_uos_qty': line.product_uom_qty,
                'product_id': line.product_id.id,
                'product_uom': line.product_uom.id,
                'price_unit': 0,
                'discount': 0,			
                'product_uom_qty': line.product_uom_qty,
                'name': sale_order_name + " / " + (line.name or "") ,
                'delay': 7,	
            }	

            sale_order_line_obj.create(cr, uid, order_line)
			

        for line in sale_order.order_line:
            vals = sale_order_line_obj.product_id_change(
                cr, uid, [line.id], sale_order.pricelist_id.id,
                product=line.product_id.id, qty=line.product_uom_qty,
                uom=line.product_uom.id, qty_uos=line.product_uos_qty,
                uos=line.product_uos.id, name=line.name,
                partner_id=sale_order.partner_id.id,
                lang=False, update_tax=True, date_order=sale_order.date_order,
                packaging=False, fiscal_position=False, flag=False, context=context)
            sale_order_line_obj.write(cr, uid, line.id, vals['value'], context=context) 
			
        return {'type': 'ir.actions.act_url', 'url': "web#id=%s&view_type=form&model=sale.order&action=359" % new_id, 'target': 'new'} 		
	
    def send_customer_tracking_no(self, cr, uid, ids, context=None):	
        mail_obj = self.pool.get('mail.mail')	
        pick = self.pool.get('stock.picking').browse(cr,uid,ids[0],context=context)
        if not pick or not pick.partner_id.email: return False
        cname = pick.partner_id.name
        #orderno = pick.sale_id.client_order_ref
        orderno = pick.sale_id.origin
        carrier = pick.carrier_id.name or "FedEx"		
        tracking_no = pick.carrier_tracking_ref
        if not tracking_no :
            raise osv.except_osv(_('Error'), _('No Tracking Number!!!'))
			
        body_msg = u'<pre>Dear %s, <br/><br/> Thank you very much for your order %s, which we have shipped today with %s under tracking number %s.<br/><br/> We hope you are satisfied with our service and hope to serve you soon again!<br/><br/>Best regards,<br/>Nomi Tang - Shipping Department</pre>' %	(cname, orderno, carrier, tracking_no)		
        bcc = 'arnd.krusche@loewie.com,ray.kwok@loewie.com,chifai.yuen@loewie.com,anthony.chau@loewie.com,anja.wang@loewie.com,jimmy.lee@loewie.com,emma.wang@loewie.com'
        #bcc = '2336884512@qq.com'		
        vals = {    
                    'state':'outgoing',
                    'subject':'Your Nomi Tang order %s has been shipped today!' % orderno,						 
                    'body_html': body_msg,
                    'email_to': pick.partner_id.email or ( pick.sale_id and pick.sale_id.partner_id.email ),						
                    #'email_cc': '2336884512@qq.com',						 
                    #'email_cc':'arnd.krusche@loewie.com,anthony.chau@loewie.com,anja.wang@loewie.com,jimmy.lee@loewie.com',
                    'email_from': 'sales@nomitang.com',
                }
        mail_id = mail_obj.create(cr, uid, vals, context=context)
        if mail_id : 
            #res = mail_obj.send(cr, uid, [mail_id], context=context)		
            res = mail_obj.send(cr, uid, [mail_id], bcc=bcc, context=context)	
            self.message_post(cr, uid, ids, body="Customer Notification Message Body:"+ chr(10) + body_msg, context=context)			
			
        return True		