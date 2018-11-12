#This file is part of Tryton.  The COPYRIGHT file at the top level of
#this repository contains the full copyright notices and license terms.
import datetime
from trytond.wizard import StateAction, Button
from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool
from trytond.model import fields

__all__ = ['ProductsByLocationsStart', 'ProductsByLocations']


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

        def get_location_name(location):
            name = location.name.strip()
            code = location.code.strip() if location.code else None
            return ("%s [%s]" % (name, code)) if code else name

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
            locations = Location.browse(location_ids)
            if len(locations) == 1:
                data['locations'] = get_location_name(locations[0])
            else:
                data['locations'] = "/ ".join(
                    get_location_name(location) for location in locations)
        else:
            data['locations'] = ""

        return action, data
