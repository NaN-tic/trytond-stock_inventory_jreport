# This file is part of stock_inventory_jreport module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool

import inventory
import location


def register():
    Pool.register(
        inventory.InventoryReport,
        inventory.BlindCountReport,
        inventory.InventoryValuedReport,
        module='stock_inventory_jreport', type_='report')
    Pool.register(
        location.ProductsByLocations,
        module='stock_inventory_jreport', type_='wizard')
