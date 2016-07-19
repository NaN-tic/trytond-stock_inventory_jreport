#!/usr/bin/env python
# This file is part of stock_inventory_jreport module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import unittest
import trytond.tests.test_tryton
from trytond.tests.test_tryton import ModuleTestCase


class StockInventoryJreportTestCase(ModuleTestCase):
    'Test Stock Inventory Jreport module'
    module = 'stock_inventory_jreport'


def suite():
    suite = trytond.tests.test_tryton.suite()
    suite.addTests(unittest.TestLoader().loadTestsFromTestCase(
        StockInventoryJreportTestCase))
    return suite
