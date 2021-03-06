# -*- encoding: utf-8 -*-
# __author__ = xia.fajin@elico-corp.com
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2012 Cubic ERP - Teradata SAC (<http://cubicerp.com>).
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

{
    "name": "Sale Order Lines Discount",
    "description": """

    Add function to change all  order lines discount once in sales order.
========================================================
                    """,
    "version": "0.1",
    "depends": ["sale"],
    "category": "sale",
    "author": "xia.fajin",
    "url": "http://www.elico-corp.com/",
    "data": ['sale_order_view.xml'],
    "installable": True,
    "auto_install": False,
}

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
