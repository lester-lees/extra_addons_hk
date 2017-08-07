# -*- coding: utf-8 -*-
from openerp.osv import fields,osv
from openerp import tools

class loewie_purchase_report(osv.osv):
    _name = "loewie.purchase.report"
    _description = "Loewie Purchases Orders"
    _auto = False
    _order = 'date desc, price_total desc'

    _columns = {
        'date': fields.datetime('Date Order', readonly=True),  # TDE FIXME master: rename into date_order
        'date_confirm': fields.date('Date Confirm', readonly=True),
        'year_confirm': fields.integer('Year', readonly=True),  		
        'month_confirm': fields.integer('Month', readonly=True), 		
        'order_no': fields.char(string='Order NO', readonly=True),		
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'product_name': fields.char('Product Name', readonly=True),  # 产品名字， 必须		
        'is_sample': fields.char(string='Is Sample', readonly=True),			
        'name_template': fields.char('Product Name', readonly=True),		
	    'product_type': fields.char('Product Brand'),
        'product_uom_qty': fields.integer('UOM Qty', readonly=True),
        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'delay': fields.float('Commitment Delay', digits=(16,2), readonly=True),
        'lines': fields.integer('Lines', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'state': fields.selection([ ('draft', 'Quotation'), ('sent', 'Quotation Sent'), ('waiting_date', 'Waiting Schedule'), ('manual', 'Manual In Progress'),('manager_confirm', 'Manager Confirm'), ('progress', 'In Progress'), ('invoice_except', 'Invoice Exception'), ('done', 'Done'), ('cancel', 'Cancelled') ], 'Order Status', readonly=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'country_id': fields.many2one('res.country', 'Country', readonly=True),
        'country_id': fields.many2one('res.country', 'Country', readonly=True),		
    }

    def _select(self):   
		
        select_str = """
             SELECT min(l.id) as id,
                    l.product_id as product_id,						
                    (p.name_template || ' ~ ' || coalesce( (select sum(qty) from stock_quant sq where sq.product_id = l.product_id and sq.location_id in (12,39)), 0 ) || ' , ' || coalesce( (select sum(qty) from stock_quant sq where sq.reservation_id is Null and sq.product_id = l.product_id and sq.location_id in (12,39)), 0 )) as name_template,				
		            p.product_type as product_type,
                    ( case when p.is_sample then 'True' else 'False' end) as is_sample,					
                    t.uom_id as product_uom,
                    cast(sum(l.product_uom_qty / u.factor * u2.factor) as integer) as product_uom_qty,		
                    sum(l.product_uom_qty * l.price_unit * (100.0- coalesce(l.discount, 0) ) / 100.0) as price_total,
                    count(*) as nbr,
                    s.name as sale_order,					
                    s.date_order as date,
                    s.date_confirm as date_confirm,
                    extract(YEAR from s.date_confirm) as year_confirm,					
                    extract(MONTH from s.date_confirm) as month_confirm,					
                    s.partner_id as partner_id,
                    s.user_id as user_id,
                    s.company_id as company_id,
                    extract(epoch from avg(date_trunc('day',s.date_confirm)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    l.state,
                    r.section_id as section_id,
                    r.country_id as country_id
        """
        return select_str

    def _from(self):  #  where s.state in ('done','progress','manual','shipping_except','invoice_except')
        from_str = """
                 sale_order_line l
                      join sale_order s on (l.order_id=s.id)				  
                      left join res_partner r on (s.partner_id = r.id)
                      left join res_company cp on (s.company_id = cp.id)
                    left join product_product p on (l.product_id=p.id)
                    left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_uom u on (u.id=l.product_uom)
                    left join product_uom u2 on (u2.id=t.uom_id) 
        """
        return from_str

    def _group_by(self):  #                     				
        group_by_str = """
            GROUP BY p.product_type,
		            p.name_template,					
                    p.is_sample,					
                    l.product_id,					
                    l.order_id,
                    t.uom_id,
                    year_confirm,
                    month_confirm,
                    sale_order,					
                    s.date_order,
                    s.date_confirm,
                    s.partner_id,
                    s.user_id,
                    s.company_id,
                    l.state,
                    r.section_id,
                    r.country_id				
        """
        return group_by_str

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))