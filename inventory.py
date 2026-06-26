# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime
from tempfile import NamedTemporaryFile

from babel.dates import format_datetime
from dominate.tags import div, h2, strong, style, table, tbody, td, th, thead, tr
from dominate.util import raw
from openpyxl import Workbook

from trytond.model import ModelView, fields
from trytond.modules.html_report.dominate_report import DominateReport
from trytond.modules.html_report.engine import render as html_render
from trytond.modules.html_report.i18n import _
from trytond.pool import Pool, PoolMeta
from trytond.report import Report
from trytond.rpc import RPC
from trytond.tools import grouped_slice
from trytond.transaction import Transaction
from trytond.wizard import Button, StateReport, StateView, Wizard


class TimeoutException(Exception):
    pass


class TimeoutChecker:
    def __init__(self, timeout, callback):
        self._timeout = timeout
        self._callback = callback
        self._start = datetime.now()

    @property
    def elapsed(self):
        return (datetime.now() - self._start).seconds

    def check(self):
        if self.elapsed > self._timeout:
            self._callback()


class PrintTotalInventoryStart(ModelView):
    'Print Total Inventory'
    __name__ = 'stock.inventory.print_total_inventory.start'

    date = fields.Date("Date")
    products = fields.Many2Many(
        'product.product', None, None, "Products",
        domain=[
            ('type', '=', 'goods'),
        ])
    locations = fields.Many2Many(
        'stock.location', None, None, "Locations",
        domain=[('type', '=', 'warehouse')], required=True)
    output_format = fields.Selection([
        ('pdf', "PDF"),
        ('xlsx', "Excel"),
        ('html', "HTML")],
        "Format", required=True)
    order = fields.Selection([
        ('location', 'Location'),
        ('product', 'Product'),
        ], "Order", required=True)
    quantities = fields.Selection([
        ('all', 'All'),
        ('positive', 'Positive'),
        ('negative', 'Negative'),
        ], "Quantities", required=True)
    timeout = fields.Integer('Timeout', required=True,
        help='Timeout in seconds')

    @staticmethod
    def default_locations():
        warehouse = Transaction().context.get('warehouse')
        if warehouse:
            return [warehouse]
        return []

    @staticmethod
    def default_quantities():
        return 'positive'

    @staticmethod
    def default_timeout():
        return 120

    @classmethod
    def __setup__(cls):
        Move = Pool().get('stock.move')
        super().__setup__()
        cls.products.domain = [
            ('type', 'in', Move.get_product_types()),
            ]
        try:
            Pool().get('stock.lot')
        except KeyError:
            return
        cls.group_by_lot = fields.Boolean('Group by Lot')


class PrintTotalInventory(Wizard):
    'Print Total Inventory'
    __name__ = 'stock.inventory.print_total_inventory'

    start = StateView('stock.inventory.print_total_inventory.start',
        'stock_inventory_report.print_total_inventory_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'print_', 'tryton-print', default=True),
            ])
    print_ = StateReport('stock_inventory_report.total_inventory')

    def default_start(self, fields):
        return {
            'output_format': 'pdf',
            'order': 'location',
            }

    def do_print_(self, action):
        data = {
            'date': self.start.date,
            'quantities': self.start.quantities,
            'group_by_lot': getattr(self.start, 'group_by_lot', False),
            'products': [x.id for x in self.start.products],
            'locations': [x.id for x in self.start.locations],
            'output_format': self.start.output_format,
            'order': self.start.order,
            'timeout': self.start.timeout,
            }
        if self.start.output_format == 'xlsx':
            ActionReport = Pool().get('ir.action.report')
            action_report, = ActionReport.search([
                    ('report_name', '=', 'stock_inventory_report.total_inventory_xlsx'),
                    ])
            action = action_report.action.get_action_value()
        return action, data

    def transition_print_(self):
        return 'end'


class TotalInventoryReport(DominateReport):
    'Total Inventory Report'
    __name__ = 'stock_inventory_report.total_inventory'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['execute'] = RPC(False)

    @classmethod
    def prepare(cls, data):
        pool = Pool()
        Company = pool.get('company.company')
        Date = pool.get('ir.date')
        Location = pool.get('stock.location')
        Product = pool.get('product.product')

        checker = TimeoutChecker(data.get('timeout', 60), TimeoutException)

        if data.get('group_by_lot'):
            Lot = pool.get('stock.lot')
        else:
            Lot = None

        with Transaction().set_context(_record_cache_size=100000):
            locations = Location.search([
                    ('parent', 'child_of', data['locations']),
                    ('type', '=', 'storage'),
                    ], order=[('name', 'ASC')])
        location_ids = [l.id for l in locations]
        locations_by_id = {l.id: l for l in locations}
        checker.check()

        domain = [('type', '=', 'goods')]
        if data['products']:
            domain.append(('id', 'in', data['products']))

        with Transaction().set_context(
                active_test=False, _record_cache_size=100000):
            products = Product.search(domain)
        products_by_id = {p.id: p for p in products}

        stock_date_end = data['date'] or Date.today()
        quantities = data.get('quantities', 'positive')

        records = []
        with Transaction().set_context(stock_date_end=stock_date_end):
            grouping = ('product',)
            if data.get('group_by_lot'):
                grouping += ('lot',)
            for sub_products in grouped_slice(products, count=10000):
                checker.check()
                product_ids = [x.id for x in sub_products]
                pbl = Product.products_by_location(
                    location_ids,
                    grouping=grouping,
                    grouping_filter=(product_ids,))

                for key, qty in pbl.items():
                    if not qty:
                        continue
                    if quantities == 'positive' and qty < 0:
                        continue
                    if quantities == 'negative' and qty > 0:
                        continue
                    record = {
                        'quantity': qty,
                        'location': locations_by_id[key[0]],
                        'product': products_by_id[key[1]],
                        }
                    if data.get('group_by_lot'):
                        record['lot'] = Lot(key[2]) if key[2] else None
                    records.append(record)

        company_id = Transaction().context.get('company')
        parameters = {
            'company': (Company(company_id)
                if company_id is not None and company_id >= 0 else None),
            'now': format_datetime(
                datetime.now(), format='short',
                locale=Transaction().language or 'en'),
            'sort_attribute': ('product.rec_name'
                if data['order'] == 'product' else 'location.rec_name'),
            'has_lot': data.get('group_by_lot'),
            'timeout': data.get('timeout') - checker.elapsed,
            }
        return records, parameters

    @classmethod
    def _sort_value(cls, item, sort_attribute):
        value = item
        for part in sort_attribute.split('.'):
            if isinstance(value, dict):
                value = value.get(part)
            else:
                value = getattr(value, part, '')
        return value or ''

    @classmethod
    def show_lines(cls, records, parameters):
        has_lot = parameters.get('has_lot')
        sort_attribute = parameters.get('sort_attribute')

        lines_table = table()
        with lines_table:
            with thead():
                with tr():
                    th(_('Location'))
                    th(_('Product'))
                    if has_lot:
                        th(_('Lot'))
                    th(_('Quantity'), style='text-align: right')
            with tbody():
                for record in sorted(
                        records,
                        key=lambda item: cls._sort_value(
                            item, sort_attribute)):
                    product = record['product']
                    with tr():
                        td(record['location'].name)
                        td(product.rec_name)
                        if has_lot:
                            lot = record.get('lot')
                            td(lot.rec_name if lot else '')
                        td(
                            html_render(
                                record['quantity'],
                                digits=product.default_uom.digits),
                            style='text-align: right')
        return lines_table

    @classmethod
    def title(cls, action, data, records):
        parameters = data.get('parameters', {}) if data else {}
        company = parameters.get('company')
        company_name = company.rec_name if company else ''
        now = parameters.get('now', '')
        title = _('Total Inventory')
        if company_name and now:
            return '%s - %s - %s' % (title, company_name, now)
        if company_name:
            return '%s - %s' % (title, company_name)
        if now:
            return '%s - %s' % (title, now)
        return title

    @classmethod
    def body(cls, action, data, records):
        parameters = data['parameters']
        wrapper = div()
        with wrapper:
            style(raw("""
@media print {
  #header-details {
    display: none;
  }
}
"""))
        with div(cls='container-fluid') as container:
            with div(cls='row'):
                with div(cls='col-md-12') as column:
                    h2(cls.title(action, data, records))
                    if data['records']:
                        column.add(cls.show_lines(
                            data['records'], parameters))
                    else:
                        strong(_('No records found'))
        wrapper.add(container)
        return wrapper

    @classmethod
    def execute(cls, ids, data):
        with Transaction().set_context(active_test=False):
            records, parameters = cls.prepare(data)

        return super().execute([], {
            'name': 'stock_inventory_report.total_inventory',
            'model': 'stock.inventory',
            'records': records,
            'parameters': parameters,
            'output_format': data.get('output_format', 'pdf'),
            })


class TotalInventoryXlsxReport(Report, metaclass=PoolMeta):
    __name__ = 'stock_inventory_report.total_inventory_xlsx'

    @classmethod
    def execute(cls, ids, data):
        pool = Pool()
        ActionReport = pool.get('ir.action.report')
        action_report, = ActionReport.search([
                ('report_name', '=', cls.__name__)
                ])
        cls.check_access(action_report, action_report.model, ids)
        with Transaction().set_context(active_test=False):
            records, parameters = TotalInventoryReport.prepare(data)
        content = cls.get_content(records, parameters)
        filename = action_report.name
        return 'xlsx', content, action_report.direct_print, filename

    @classmethod
    def get_content(cls, records, parameters):
        wb = Workbook()
        ws = wb.active
        ws.title = _('Total Inventory')[:31]

        title = TotalInventoryReport.title(
            None, {'parameters': parameters, 'records': records}, records)
        ws.append([title])
        company = parameters.get('company')
        if company:
            ws.append([company.rec_name])
        if parameters.get('now'):
            ws.append([parameters['now']])
        ws.append([])

        has_lot = parameters.get('has_lot')
        sort_attribute = parameters.get('sort_attribute')
        headers = [_('Location'), _('Product')]
        if has_lot:
            headers.append(_('Lot'))
        headers.append(_('Quantity'))
        ws.append(headers)

        for record in sorted(
                records,
                key=lambda item: TotalInventoryReport._sort_value(
                    item, sort_attribute)):
            product = record['product']
            row = [
                record['location'].name,
                product.rec_name,
                ]
            if has_lot:
                lot = record.get('lot')
                row.append(lot.rec_name if lot else '')
            row.append(record['quantity'])
            ws.append(row)

        with NamedTemporaryFile() as tmp_file:
            wb.save(tmp_file.name)
            tmp_file.seek(0)
            return bytes(tmp_file.read())
