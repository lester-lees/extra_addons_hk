# -*- coding: utf-8 -*-
from openerp.osv import fields,osv
from openerp import tools

class loewie_purchase_report(osv.osv):
    _name = "loewie.purchase.report"
    _description = "Loewie Purchases Orders"
    _auto = False
    _order = 'date desc, price_total desc'

    _columns = {
        'product_id': fields.integer('Product', readonly=True), # fields.many2one('product.product', 'Product', readonly=True),		
        'name_template': fields.char('Product Name', readonly=True),  # 产品名字， 必须			
        'product_stock': fields.char('Product Stock', readonly=True),		
	    'product_type': fields.char('Product Brand'),
        'product_uom_qty': fields.integer('Quantity', readonly=True),
		
        'create_date': fields.datetime('Date Order', readonly=True),  
        'date_confirm': fields.date('Date Confirm', readonly=True),
        'year_confirm': fields.integer('Year', readonly=True),  		
        'month_confirm': fields.integer('Month', readonly=True), 	
		
        'order_name': fields.char(string='Sales Order', readonly=True),		
        'partner': fields.char('Partner', readonly=True),
        'sales_person': fields.char('Salesperson', readonly=True),
        'lines': fields.integer('Lines', readonly=True),  
        'state': fields.selection([ ('draft', 'Quotation'), ('sent', 'Quotation Sent'), ('waiting_date', 'Waiting Schedule'), ('manual', 'Manual In Progress'),('manager_confirm', 'Manager Confirm'), ('progress', 'In Progress'), ('invoice_except', 'Invoice Exception'), ('done', 'Done'), ('cancel', 'Cancelled') ], 'Order Status', readonly=True),
        'section': fields.char('Sales Team'),
        'country': fields.char('Country', readonly=True),
        'company': fields.char('Company', readonly=True),		
    }

    def _select(self):   
		
        select_str = """
             SELECT min(l.id) as id,
                    l.product_id as product_id,			
                    p.name_template as name_template,						
                    ('HK_' || p.name_template || ' ~ ' || coalesce( (select sum(qty) from stock_quant sq where sq.product_id = l.product_id and sq.location_id in (12,35)), 0 ) || ' , ' || coalesce( (select sum(qty) from stock_quant sq where sq.reservation_id is Null and sq.product_id = l.product_id and sq.location_id in (12,35)), 0 )) as product_stock,				
		            p.product_type as product_type,			
                    cast(sum(l.product_uom_qty) as integer) as product_uom_qty,	

                    s.date_order as create_date,
                    s.date_confirm as date_confirm,
                    cast(extract(YEAR from s.date_confirm) as integer) as year_confirm,					
                    cast(extract(MONTH from s.date_confirm) as integer) as month_confirm,	
					
                    s.name as order_name,	
                    r.name as partner,					
                    ru.login as sales_person,
                    count(*) as lines,					
                    l.state as state,
                    ccs.name as section,
                    rc.name as country,
                    cp.name as company					
        """
        return select_str

    def _from(self):  
        from_str = """
                sale_order_line l
                    join sale_order s on (l.order_id=s.id)				  
                    left join res_partner r on (s.partner_id = r.id)
                    left join res_company cp on (s.company_id = cp.id)
                    left join product_product p on (l.product_id=p.id)
                    left join product_template t on (p.product_tmpl_id=t.id)
                    left join res_country rc on (r.country_id=rc.id)	
                    left join crm_case_section ccs on (r.section_id=ccs.id)	
                    left join res_users ru on (s.user_id=ru.id)					
        """
        return from_str

    def _group_by(self):  #                     				
        group_by_str = """
            GROUP BY l.product_id,
		            name_template, 
                    product_stock,
                    product_type,										

                    year_confirm,
                    month_confirm,
                    s.date_order,
                    date_confirm,
					
                    order_name,
                    partner,
                    sales_person,
                    l.state,
                    section,
                    country,
                    company					
        """
        return group_by_str

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))