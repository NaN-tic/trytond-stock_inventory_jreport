# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import os
from datetime import datetime
from babel.dates import format_datetime
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateReport, Button
from trytond.rpc import RPC
from trytond.modules.html_report.html_report import HTMLReport


class PrintTotalInventoryStart(ModelView):
    'Print Total Inventory'
    __name__ = 'stock.inventory.print_total_inventory.start'

    date = fields.Date("Date")
    products = fields.Many2Many(
        'product.product', None, None, "Products")
    locations = fields.Many2Many(
        'stock.location', None, None, "Locations",
        domain=[('type', '=', 'warehouse')], required=True)
    output_format = fields.Selection([
        ('pdf', "PDF"),
        ('xls', "Excel"),
        ('html', "HTML")],
        "Format", required=True)
    order = fields.Selection([
        ('location_name', 'Location Name'),
        ('product_name', 'Product Name'),
        ('product_code', 'Product Code'),
        ], "Order", required=True)


class PrintTotalInventory(Wizard):
    'Print Total Inventory'
    __name__ = 'stock.inventory.print_total_inventory'

    start = StateView('stock.inventory.print_total_inventory.start',
        'stock_inventory_jreport.print_total_inventory_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateReport('stock_inventory_jreport.total_inventory')

    def default_start(self, fields):
        return {
            'output_format': 'pdf',
            'order': 'location_name',
        }

    def do_print_(self, action):
        data = {
            'date': self.start.date,
            'products': [x.id for x in self.start.products],
            'locations': [x.id for x in self.start.locations],
            'output_format': self.start.output_format,
            'order': self.start.order,
            }
        return action, data

    def transition_print_(self):
        return 'end'


class TotalInventoryReport(HTMLReport):
    'Total Inventory Report'
    __name__ = 'stock_inventory_jreport.total_inventory'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['execute'] = RPC(False)

    @classmethod
    def prepare(cls, data):
        pool = Pool()
        Company = pool.get('company.company')
        Location = pool.get('stock.location')
        Date = pool.get('ir.date')
        Product = pool.get('product.product')

        try:
            Lot = pool.get('stock.lot')
        except KeyError:
            Lot = None

        locations = {}
        locations_ids = []

        for location in Location.search([
                ('parent', 'child_of', data['locations']),
                ('type', '=', 'storage')], order=[('name', 'ASC')]):
            locations_ids.append(location.id)
            locations[location.id] = location

        if data['products']:
            query = [('id', 'in', data['products'])]
        else:
            query = []

        products = {}
        for product in Product.search(query):
            products[product.id] = product

        if data['date']:
            stock_date_end = data['date']
        else:
            stock_date_end = Date.today()

        products_ids = list(products.keys())

        records = []
        with Transaction().set_context(stock_date_end=stock_date_end):
            if Lot:
                pbl = list(Product.products_by_location(locations_ids,
                    products_ids, grouping=('product', 'lot')).items())
            else:
                pbl = Product.products_by_location(locations_ids,
                    products_ids).items()

            for key, value in pbl:
                if value > 0 and key[1] in products_ids:
                    record = {}
                    record['quantity'] = value
                    record['location'] = locations[key[0]]
                    record['product'] = products[key[1]]
                    if Lot:
                        record['lot'] = Lot(key[2]) if key[2] else None
                    records.append(record)

        company_id = Transaction().context.get('company')

        parameters = {}
        parameters['company'] = Company(company_id) if company_id else ''
        parameters['now'] = format_datetime(datetime.now(), format='short',
            locale=Transaction().language or 'en')
        parameters['sort_atribute'] = 'location.name'
        if data['order'] == 'product_name':
            parameters['sort_atribute'] = 'product.name'
        elif data['order'] == 'product_code':
            parameters['sort_atribute'] = 'product.code'
        parameters['has_lot'] = True if Lot else False

        return records, parameters

    @classmethod
    def execute(cls, ids, data):
        with Transaction().set_context(active_test=False):
            records, parameters = cls.prepare(data)

        context = Transaction().context
        context['report_lang'] = Transaction().language
        context['report_translations'] = os.path.join(
                os.path.dirname(__file__), 'translations')

        with Transaction().set_context(**context):
            name = 'stock_inventory_jreport.total_inventory'
            return super().execute([], {
                'name': name,
                'model': 'stock.inventory',
                'records': records,
                'parameters': parameters,
                'output_format': data.get('output_format', 'pdf'),
                })
