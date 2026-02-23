# This file is part of stock_inventory_jreport module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import inventory
from . import location
from . import product
from .total_inventory import total_inventory

def register():
    module = 'stock_inventory_jreport'
    Pool.register(
        location.Location,
        product.Product,
        module=module, type_='model')
    Pool.register(
        inventory.InventoryReport,
        inventory.BlindCountReport,
        inventory.InventoryValuedReport,
        inventory.LocationInventoryValuedReport,
        module=module, type_='report')

    Pool.register(
        total_inventory.PrintTotalInventoryStart,
        module=module, type_='model')
    Pool.register(
        total_inventory.PrintTotalInventory,
        module=module, type_='wizard')
    Pool.register(
        total_inventory.TotalInventoryReport,
        total_inventory.TotalInventoryXlsxReport,
        module=module, type_='report')
