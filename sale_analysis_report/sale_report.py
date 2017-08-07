# -*- coding: utf-8 -*-
from openerp import tools
from openerp.osv import fields, osv


class productProduct(osv.osv):
    _inherit = "product.product"
    _columns = {
        'gross_cost':fields.float(string='Gross Cost',groups="account.group_account_manager"),	 # 
    }		

class sale_report(osv.osv):
    _inherit = "sale.report"
    _description = "Sales Orders Statistics"
    _auto = False
    _rec_name = 'date'
	
    def calc(self, cr, uid, ids, context=None):
        res = {}
        for product in self.browse(cr, uid, ids):
            res[product.id] = len(product.product_variant_ids)
        return res
		
    _columns = {
        'date': fields.datetime('Date Order', readonly=True),  # TDE FIXME master: rename into date_order
        'date_confirm': fields.date('Date Confirm', readonly=True),
        'year_confirm': fields.integer('Year', readonly=True),  		
        'month_confirm': fields.integer('Month', readonly=True), 		
        'sale_order': fields.char(string='Sales Order', readonly=True),		
        'product_id': fields.many2one('product.product', 'Product', readonly=True),
        'is_sample': fields.char(string='Is Sample', readonly=True),			
        'name_template': fields.char('Product Name', readonly=True),		
	    'product_type': fields.char('Product Brand'),
        'product_uom': fields.many2one('product.uom', 'Unit of Measure', readonly=True),
        'product_uom_qty': fields.integer('UOM Qty', readonly=True),

        'partner_id': fields.many2one('res.partner', 'Partner', readonly=True),
        'company_id': fields.many2one('res.company', 'Company', readonly=True),
        'user_id': fields.many2one('res.users', 'Salesperson', readonly=True),
        'price_total': fields.float('Total Price', readonly=True),
        'delay': fields.float('Commitment Delay', digits=(16,2), readonly=True),
        'categ_id': fields.many2one('product.category','Category of Product', readonly=True),
        'nbr': fields.integer('# of Lines', readonly=True),  # TDE FIXME master: rename into nbr_lines
        'state': fields.selection([ ('draft', 'Quotation'), ('sent', 'Quotation Sent'), ('waiting_date', 'Waiting Schedule'), ('manual', 'Manual In Progress'),('manager_confirm', 'Manager Confirm'), ('progress', 'In Progress'), ('invoice_except', 'Invoice Exception'), ('done', 'Done'), ('cancel', 'Cancelled') ], 'Order Status', readonly=True),
        'pricelist_id': fields.many2one('product.pricelist', 'Pricelist', readonly=True),
        'analytic_account_id': fields.many2one('account.analytic.account', 'Analytic Account', readonly=True),
        'section_id': fields.many2one('crm.case.section', 'Sales Team'),
        'country_id': fields.many2one('res.country', 'Country', readonly=True),
        'currency_id': fields.many2one('res.currency', 'Currency', readonly=True),
        'standard_currency_id': fields.many2one('res.currency', 'Invoice Currency', readonly=True),
        'price_usd': fields.float('Price_USD', readonly=True),
        'price_hkd': fields.float('Price_HKD', readonly=True),	
        'product_cost': fields.char('Product Cost',readonly=True),	 # ,groups="account.group_account_manager"
        'total_cost': fields.float('Total Cost',readonly=True),  #  ,groups="account.group_account_manager"
        'profit_usd': fields.float(string='Profit USD',readonly=True),   # ,groups="account.group_account_manager"
    }
    _order = 'date desc'

    def _select(self):   
	
        # (select cast(gross_cost as text) from product_product where id=l.product_id) as gross_cost,		
        # select id from stock_location where usage='internal' and scrap_location = False	===> (12,35)), to include TMall JD location# location_id 12 = Stock, 35 = TMallJD
        # p.gross_cost as single_cost, 		
        select_str = """
             SELECT min(l.id) as id,
                    l.product_id as product_id,						
                    (p.name_template || ' ~ ' || coalesce( (select sum(qty) from stock_quant sq where sq.product_id = l.product_id and sq.location_id in (12,35)), 0 ) || ' , ' || coalesce( (select sum(qty) from stock_quant sq where sq.reservation_id is Null and sq.product_id = l.product_id and sq.location_id in (12,35)), 0 )) as name_template,				
		            p.product_type as product_type,
                    ( case when p.is_sample then 'True' else 'False' end) as is_sample,					
                    t.uom_id as product_uom,
                    cast(sum(l.product_uom_qty / u.factor * u2.factor) as integer) as product_uom_qty,		

                    (p.name_template || ' ~ ' || coalesce( p.gross_cost, 0 ) ) as product_cost,					
                    										
                    ( sum(l.product_uom_qty) * p.gross_cost ) as total_cost,
					
                    ( sum( ( l.product_uom_qty * l.price_unit * (100.0- coalesce(l.discount,0) ) / 100.0 ) /
                    (SELECT rate FROM res_currency_rate 
                       WHERE currency_id = pl.currency_id
                         AND create_date <= s.date_order 
                       ORDER BY create_date desc LIMIT 1)
                        -  l.product_uom_qty * p.gross_cost ) ) as profit_usd,  
						
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
                    t.categ_id as categ_id,
                    s.pricelist_id as pricelist_id,
                    s.project_id as analytic_account_id,
                    r.section_id as section_id,
                    r.country_id as country_id,
                    pl.currency_id as currency_id,
                    cp.currency_id as standard_currency_id,
                    sum((l.product_uom_qty * l.price_unit * (100.0- coalesce(l.discount,0) ) / 100.0) /
                    (SELECT rate FROM res_currency_rate 
                       WHERE currency_id = pl.currency_id
                         AND create_date <= s.date_order 
                       ORDER BY create_date desc LIMIT 1)
                       ) as price_usd, 
                    sum((l.product_uom_qty * l.price_unit * (100.0- coalesce(l.discount,0) ) / 100.0) /					   
                   (SELECT rate FROM res_currency_rate 
                       WHERE currency_id = pl.currency_id
                         AND create_date <= s.date_order 
                       ORDER BY create_date desc LIMIT 1) *
                    (SELECT rate FROM res_currency_rate 
                       WHERE currency_id = (select id from res_currency where name='HKD' limit 1)
                         AND create_date <= s.date_order 
                       ORDER BY create_date desc LIMIT 1)
                       ) as price_hkd					   

        """
        return select_str

    def _from(self):
        from_str = """
                 sale_order_line l
                      join sale_order s on (l.order_id=s.id)				  
                      left join res_partner r on (s.partner_id = r.id)
                      left join product_pricelist pl on (s.pricelist_id = pl.id)
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
                    t.categ_id,
                    year_confirm,
                    month_confirm,
                    sale_order,					
                    s.date_order,
                    s.date_confirm,
                    s.partner_id,
                    s.user_id,
                    s.company_id,
                    l.state,
                    s.pricelist_id,
                    s.project_id,
                    r.section_id,
                    r.country_id,
                    pl.currency_id,
                    cp.currency_id,
                    product_cost,
                    p.gross_cost					
        """
        return group_by_str

    def init(self, cr):
        tools.drop_view_if_exists(cr, self._table)
        cr.execute("""CREATE or REPLACE VIEW %s as (
            %s
            FROM ( %s )
            %s
            )""" % (self._table, self._select(), self._from(), self._group_by()))