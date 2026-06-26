# This file is part of stock_inventory_report module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool

from . import inventory


def register():
    module = 'stock_inventory_report'
    Pool.register(
        inventory.PrintTotalInventoryStart,
        module=module, type_='model')
    Pool.register(
        inventory.PrintTotalInventory,
        module=module, type_='wizard')
    Pool.register(
        inventory.TotalInventoryReport,
        inventory.TotalInventoryXlsxReport,
        module=module, type_='report')
