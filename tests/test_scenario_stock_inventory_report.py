import datetime as dt
import unittest
from decimal import Decimal

from proteus import Model, Wizard
from trytond.modules.company.tests.tools import create_company, get_company
from trytond.modules.currency.tests.tools import get_currency
from trytond.tests.test_tryton import drop_db
from trytond.tests.tools import activate_modules


class TestStockInventoryReport(unittest.TestCase):

    def setUp(self):
        drop_db()
        super().setUp()

    def tearDown(self):
        drop_db()
        super().tearDown()

    def test(self):
        activate_modules(['stock_inventory_report', 'stock_valued'])

        create_company()
        get_company()
        currency = get_currency()

        ProductUom = Model.get('product.uom')
        unit, = ProductUom.find([('name', '=', 'Unit')])

        ProductTemplate = Model.get('product.template')

        template1 = ProductTemplate()
        template1.name = 'Product 1'
        template1.code = 'P1'
        template1.default_uom = unit
        template1.type = 'goods'
        template1.list_price = Decimal('20')
        template1.cost_price_method = 'fixed'
        template1.save()
        product1, = template1.products
        product1.cost_price = Decimal('5')
        product1.save()

        template2 = ProductTemplate()
        template2.name = 'Product 2'
        template2.code = 'P2'
        template2.default_uom = unit
        template2.type = 'goods'
        template2.list_price = Decimal('20')
        template2.cost_price_method = 'fixed'
        template2.save()
        product2, = template2.products
        product2.cost_price = Decimal('7')
        product2.save()

        Location = Model.get('stock.location')
        warehouse, = Location.find([('code', '=', 'WH')])
        storage_loc, = Location.find([('code', '=', 'STO')])
        supplier_loc, = Location.find([('code', '=', 'SUP')])

        StockMove = Model.get('stock.move')
        today = dt.date.today()

        move1 = StockMove()
        move1.product = product1
        move1.unit = product1.default_uom
        move1.quantity = 5
        move1.from_location = supplier_loc
        move1.to_location = storage_loc
        move1.planned_date = today
        move1.effective_date = today
        move1.unit_price = Decimal('5')
        move1.currency = currency

        move2 = StockMove()
        move2.product = product2
        move2.unit = product2.default_uom
        move2.quantity = 3
        move2.from_location = supplier_loc
        move2.to_location = storage_loc
        move2.planned_date = today
        move2.effective_date = today
        move2.unit_price = Decimal('7')
        move2.currency = currency
        StockMove.click([move1, move2], 'do')

        Inventory = Model.get('stock.inventory')
        inventory = Inventory()
        inventory.location = storage_loc
        inventory.empty_quantity = 'keep'
        inventory.save()
        inventory.click('complete_lines')
        lines = {line.product.id: line for line in inventory.lines}
        lines[product1.id].quantity = 4
        lines[product2.id].quantity = 3
        inventory.save()
        inventory.click('confirm')

        Product = Model.get('product.product')
        wizard = Wizard('stock.inventory.print_total_inventory')
        wizard.form.locations.append(Location(warehouse.id))
        wizard.form.products.append(Product(product1.id))
        wizard.form.products.append(Product(product2.id))
        wizard.form.quantities = 'positive'
        wizard.form.order = 'location'
        wizard.form.output_format = 'pdf'
        wizard.form.timeout = 120
        wizard.execute('print_')
        self.assertEqual(len(wizard.actions), 1)
        oext, content, _, _ = wizard.actions[0]
        self.assertEqual(oext, 'pdf')
        self.assertIsInstance(content, bytes)

        wizard = Wizard('stock.inventory.print_total_inventory')
        wizard.form.locations.append(Location(warehouse.id))
        wizard.form.products.append(Product(product1.id))
        wizard.form.products.append(Product(product2.id))
        wizard.form.quantities = 'positive'
        wizard.form.order = 'location'
        wizard.form.output_format = 'html'
        wizard.form.timeout = 120
        wizard.execute('print_')
        self.assertEqual(len(wizard.actions), 1)
        oext, content, _, _ = wizard.actions[0]
        self.assertEqual(oext, 'html')
        self.assertIsInstance(content, str)
        self.assertIn('Total Inventory', content)

        wizard = Wizard('stock.inventory.print_total_inventory')
        wizard.form.locations.append(Location(warehouse.id))
        wizard.form.products.append(Product(product1.id))
        wizard.form.products.append(Product(product2.id))
        wizard.form.quantities = 'positive'
        wizard.form.order = 'location'
        wizard.form.output_format = 'xlsx'
        wizard.form.timeout = 120
        wizard.execute('print_')
        self.assertEqual(len(wizard.actions), 1)
        oext, content, _, _ = wizard.actions[0]
        self.assertEqual(oext, 'xlsx')
        self.assertIsInstance(content, bytes)
        self.assertTrue(content.startswith(b'PK'))
