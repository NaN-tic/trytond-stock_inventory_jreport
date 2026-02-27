# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from datetime import datetime
from tempfile import NamedTemporaryFile
from babel.dates import format_datetime
from trytond.pool import Pool, PoolMeta
from trytond.transaction import Transaction
from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateView, StateReport, Button
from trytond.rpc import RPC
from trytond.tools import grouped_slice
from trytond.report import Report
from trytond.modules.html_report.dominate_report import DominateReport
from trytond.modules.html_report.i18n import _
from dominate.util import raw
from dominate.tags import div, h2, strong, style, table, tbody, td, th, thead, tr
from openpyxl import Workbook

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
        ('xls', "Excel"),
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
    timeout = fields.Integer('Timeout', required=True, help='Timeout in seconds')

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
            Lot = Pool().get('stock.lot')
        except KeyError:
            Lot = None
        if Lot:
            cls.group_by_lot = fields.Boolean('Group by Lot')


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
            action, = ActionReport.search([
                    ('report_name', '=', 'stock_inventory_jreport.total_inventory_xlsx'),
                    ])
        return action, data

    def transition_print_(self):
        return 'end'


class TotalInventoryReport(DominateReport):
    'Total Inventory Report'
    __name__ = 'stock_inventory_jreport.total_inventory'

    @classmethod
    def __setup__(cls):
        super().__setup__()
        cls.__rpc__['execute'] = RPC(False)

    @classmethod
    def get_grouping(data):
        return ('product',)

    @classmethod
    def prepare(cls, data):
        pool = Pool()
        Company = pool.get('company.company')
        Location = pool.get('stock.location')
        Date = pool.get('ir.date')
        Product = pool.get('product.product')

        checker = TimeoutChecker(data.get('timeout', 60), TimeoutException)

        if data.get('group_by_lot'):
            Lot = pool.get('stock.lot')
        else:
            Lot = None

        # As locations are going to be accessed randomly we need to use a large
        # cache to prevent cache trashing
        with Transaction().set_context(_record_cache_size=100000):
            locations = Location.search([
                    ('parent', 'child_of', data['locations']),
                    ('type', '=', 'storage'),
                    ], order=[('name', 'ASC')])
        location_ids = [l.id for l in locations]
        locations_by_id = dict((l.id, l) for l in locations)
        checker.check()

        domain = [('type', '=', 'goods')]
        if data['products']:
            domain.append(('id', 'in', data['products']))

        # As products are going to be accessed randomly we need to use a large
        # cache to prevent cache trashing
        with Transaction().set_context(active_test=False, _record_cache_size=100000):
            products = Product.search(domain)
        products_by_id = dict((p.id, p) for p in products)

        if data['date']:
            stock_date_end = data['date']
        else:
            stock_date_end = Date.today()

        quantities = data.get('quantities', 'positive')

        records = []
        with Transaction().set_context(stock_date_end=stock_date_end):
            grouping = ('product',)
            if data.get('group_by_lot'):
                grouping += ('lot',)
            for sub_products in grouped_slice(products, count=10000):
                checker.check()
                product_ids = [x.id for x in sub_products]
                pbl = Product.products_by_location(location_ids,
                    grouping=grouping,
                    grouping_filter=(product_ids,))

                for key, qty in pbl.items():
                    if not qty:
                        continue
                    if quantities == 'positive' and qty < 0:
                        continue
                    elif quantities == 'negative' and qty > 0:
                        continue

                    location_id = key[0]
                    product_id = key[1]
                    record = {}
                    record['quantity'] = qty
                    record['location'] = locations_by_id[location_id]
                    record['product'] = products_by_id[product_id]
                    if data.get('group_by_lot'):
                        record['lot'] = Lot(key[2]) if key[2] else None
                    records.append(record)

        company_id = Transaction().context.get('company')

        parameters = {}
        parameters['company'] = (Company(company_id)
            if company_id is not None and company_id >= 0 else '')
        parameters['now'] = format_datetime(datetime.now(), format='short',
            locale=Transaction().language or 'en')
        if data['order'] == 'product':
            parameters['sort_atribute'] = 'product.rec_name'
        else:
            parameters['sort_atribute'] = 'location.rec_name'
        parameters['has_lot'] = data.get('group_by_lot')
        parameters['timeout'] = data.get('timeout') - checker.elapsed
        return records, parameters

    @classmethod
    def show_lines(cls, records, parameters):
        render = cls.render
        has_lot = parameters.get('has_lot')
        sort_attribute = parameters.get('sort_atribute')

        def _sort_value(item):
            value = item
            for part in sort_attribute.split('.'):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = getattr(value, part, '')
            return value or ''

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
                for record in sorted(records, key=_sort_value):
                    product = record['product']
                    with tr():
                        td(record['location'].name)
                        td(product.rec_name)
                        if has_lot:
                            lot = record.get('lot')
                            td(lot.rec_name if lot else '')
                        td(render(record['quantity'],
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
            title = '%s - %s - %s' % (title, company_name, now)
        elif company_name:
            title = '%s - %s' % (title, company_name)
        elif now:
            title = '%s - %s' % (title, now)
        return title

    @classmethod
    def body(cls, action, data, records):
        parameters = data['parameters']
        title = cls.title(action, data, records)
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
                    h2(title)
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

        name = 'stock_inventory_jreport.total_inventory'
        return super().execute([], {
            'name': name,
            'model': 'stock.inventory',
            'records': records,
            'parameters': parameters,
            'output_format': data.get('output_format', 'pdf'),
            })

class TotalInventoryXlsxReport(Report, metaclass=PoolMeta):
    __name__ = 'stock_inventory_jreport.total_inventory_xlsx'

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
        content = cls.get_content(records, parameters, data)
        filename = action_report.name
        return 'xlsx', content, action_report.direct_print, filename

    @classmethod
    def get_content(cls, records, parameters, data):
        render = TotalInventoryReport.render
        wb = Workbook()
        ws = wb.active
        ws.title = _('Total Inventory')[:31]

        def xls(value, **kwargs):
            if isinstance(value, str):
                try:
                    return float(value.replace(',', '.'))
                except ValueError:
                    return value
            return value

        title = TotalInventoryReport.title(
            None,
            {
                'parameters': parameters,
                'records': records,
            },
            records)
        ws.append([title])
        company = parameters.get('company')
        if company:
            ws.append([company.rec_name])
        if parameters.get('now'):
            ws.append([parameters['now']])
        ws.append([])

        has_lot = parameters.get('has_lot')
        sort_attribute = parameters.get('sort_atribute')

        def _sort_value(item):
            value = item
            for part in sort_attribute.split('.'):
                if isinstance(value, dict):
                    value = value.get(part)
                else:
                    value = getattr(value, part, None)
            return value

        headers = [_('Location'), _('Product')]
        if has_lot:
            headers.append(_('Lot'))
        headers.append(_('Quantity'))
        ws.append(headers)

        for record in sorted(records, key=_sort_value):
            product = record['product']
            row = [
                record['location'].name,
                product.rec_name,
                ]
            if has_lot:
                lot = record.get('lot')
                row.append(lot.rec_name if lot else '')
            row.append(xls(render(
                record['quantity'], digits=product.default_uom.digits)))
            ws.append(row)

        with NamedTemporaryFile() as tmp_file:
            wb.save(tmp_file.name)
            tmp_file.seek(0)
            return bytes(tmp_file.read())
