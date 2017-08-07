# -*- coding: utf-8 -*-

from openerp import fields, models, api, _

        
class loewie_sqltool(models.Model):
    _name = 'loewie.sqltool'
	
    name = fields.Char(string="Name", required=True)	
    statement = fields.Char(string="Statement")	
    history1 = fields.Char(string="history1")		
    history2 = fields.Char(string="history2")		
    history3 = fields.Char(string="history3")		
    note = fields.Char(string="Note")	
            

    def execute_statement(self, cr, uid, ids, context=None):	
        if self.statement :
            cr.execute( self.statement )
            
            self.write({'com_ids': [(6, 0, com_ids)]})
        return True	
		
    def update_sale_order_total(self, cr, uid, ids, context=None):	
        if not self.statement :
            return
 
        statement2 = "update sale_order set amount_total=(select round( sum( price_unit * product_uom_qty * (100 - discount) / 100 ), 2) from sale_order_line where order_id=(select id from sale_order where name='%')) where name='%';select id,name,amount_total, amount_untaxed from sale_order where name='%'" % (self.statement,self.statement,self.statement)
		
        cr.execute( self.statement )
		
        return True			