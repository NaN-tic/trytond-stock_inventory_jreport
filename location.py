#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import datetime
from trytond.wizard import StateAction, Button
from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool
from trytond.model import fields

__all__ = ['ProductsByLocationsStart', 'Location', 'ProductsByLocations']


class ProductsByLocationsStart:
    __metaclass__ = PoolMeta
    __name__ = 'stock.products_by_locations.start'
    output_format = fields.Selection([
            ('pdf', 'PDF'),
            ('xls', 'XLS'),
            ], 'Output Format', required=True)

    @staticmethod
    def default_output_format():
        return 'pdf'


class Location:
    __metaclass__ = PoolMeta
    __name__ = 'stock.location'

    def report_title(self):
        if self.code:
            return ("%s [%s]" % (self.name.strip(), self.code.strip()))
        return ("%s" % (self.name.strip()))


class ProductsByLocations:
    __metaclass__ = PoolMeta
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

        output_format = self.start.output_format or 'pdf'

        context = {}
        location_ids = Transaction().context.get('active_ids')
        context['locations'] = location_ids
        context['stock_date_end'] = (self.start.forecast_date or
            datetime.date.max)

        with Transaction().set_context(context):
            psbls = Product.search([
                'OR', ('quantity','!=',0), ('forecast_quantity', '!=', 0.0)])

        data = {
            'ids': [pbl.id for pbl in psbls],
            'context': context,
            'output_format': output_format,
            }

        if location_ids:
            data['locations'] = ' / '.join([
                l.report_title() for l in Location.browse(location_ids)])
        else:
            data['locations'] = ""
        return action, data
