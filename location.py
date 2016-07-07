#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import datetime
from trytond.wizard import StateAction, Button
from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool

__all__ = ['ProductsByLocations']
__metaclass__ = PoolMeta


class ProductsByLocations:
    __name__ = 'stock.products_by_locations'

    print_ = StateAction(
        'stock_inventory_jreport.stock_inventory_valued_report_action')

    @classmethod
    def __setup__(cls):
        super(ProductsByLocations, cls).__setup__()
        cls.start.buttons.insert(1,
            Button('Print', 'print_', 'tryton-print')
            )

    def transition_print_(self):
        return 'end'

    def do_print_(self, action):
        pool = Pool()
        Location = pool.get('stock.location')
        Product = pool.get('product.product')

        context = {}
        locations = Transaction().context.get('active_ids')
        context['locations'] = locations
        context['stock_date_end'] = (self.start.forecast_date or
            datetime.date.max)

        with Transaction().set_context(context):
            psbls = Product.search([
                'OR', ('quantity','!=',0), ('forecast_quantity', '!=', 0.0)])

        data = {
            'ids': [pbl.id for pbl in psbls],
            'context': context
            }

        locations = Location.browse(locations)
        if len(locations) == 1:
            data['locations'] = ("%s [%s]" % (locations[0].name.strip(),
                    locations[0].code.strip()))
        elif len(locations) > 1:
            ls = []
            for l in Location.browse(locations):
                ls.append("%s [%s]" % (l.name.strip(), l.code.strip()))
            data['locations'] = "/ ".join(ls)
        else:
            data['locations'] = ""
        return action, data
