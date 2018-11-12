# This file is part of stock_inventory_jreport module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool
from . import inventory
from . import location
from . import product

def register():
    Pool.register(
        location.Location,
        product.Product,
        module='stock_inventory_jreport', type_='model')
    Pool.register(
        inventory.InventoryReport,
        inventory.BlindCountReport,
        inventory.InventoryValuedReport,
        module='stock_inventory_jreport', type_='report')
