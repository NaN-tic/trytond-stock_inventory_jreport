# This file is part of stock_inventory_jreport module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import Pool

from .inventory import *
from .location import *


def register():
    Pool.register(
        Inventory,
        module='stock_inventory_jreport', type_='report')
    Pool.register(
        ProductsByLocations,
        module='stock_inventory_jreport', type_='wizard')
