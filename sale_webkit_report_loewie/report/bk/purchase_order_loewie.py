import time
from openerp.report import report_sxw
from openerp.osv import osv


class purchase_printout_loewie(report_sxw.rml_parse):
    
    def _update_dict_when_key_purchase_currency_none(self, line_pur_cur, res):
        if line_pur_cur.id not in res.keys():
            res[line_pur_cur.id] = {
                    'group_pur_cur': line_pur_cur,
                    'group_pur_total': 0,
                    'group_discount': 0,
                    'group_pur_subtotal': 0,
                    'group_price_subtotal': 0,
                    'group_lines': [],
                }
        return res

    def get_pur_lines_groups(self, lines, inv_cur):
        # for gr in lines_by_pur_group:
        res = {}
        for line in lines:
            line_pur_cur = line.pur_currency_id

            # prepare res if no purchase keys
            res = self._update_dict_when_key_purchase_currency_none(
                line_pur_cur, res)

            # update line value in
            oldgr = res[line_pur_cur.id]
            res[line_pur_cur.id].update({
                'group_pur_total': oldgr['group_pur_total'] + line.pur_price_subtotal,
                'group_discount': 0,
                'group_pur_subtotal': oldgr['group_pur_subtotal']+ line.pur_price_subtotal,
                'group_price_subtotal': oldgr['group_price_subtotal'] + line.price_subtotal,
            })
            oldgr['group_lines'].append(line)

        return res

    def __init__(self, cr, uid, name, context): 
        super(purchase_printout_loewie, self).__init__(cr, uid, name, context=context)
        self.localcontext.update({
            'time': time,
            'cr':cr,
            'uid': uid,
            'get_pur_lines_groups': self.get_pur_lines_groups,
        })
        self.context = context


class purchase_printout_loewie_document(osv.AbstractModel):
    _name = 'report.sale_webkit_report_loewie.report_purchase_order_loewie'
    _inherit = 'report.abstract_report'
    _template = 'sale_webkit_report_loewie.report_purchase_order_loewie'
    _wrapped_report_class = purchase_printout_loewie

class purchase_printout_loewie_document(osv.AbstractModel):
    _name = 'report.sale_webkit_report_loewie.po_without_price'
    _inherit = 'report.abstract_report'
    _template = 'sale_webkit_report_loewie.po_without_price'
    _wrapped_report_class = purchase_printout_loewie

