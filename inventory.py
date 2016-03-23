# This file is part of stock_inventory_jasper module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.modules.jasper_reports.jasper import JasperReport
from trytond.transaction import Transaction
from trytond.pool import PoolMeta


__all__ = ['Inventory']
__metaclass__ = PoolMeta


class Inventory(JasperReport):
    __name__ = 'stock.inventory.jreport'

    @classmethod
    def execute(cls, ids, data):
        if 'locations' in data:
            if 'parameters' not in data:
                data['parameters'] = {}
            data['parameters']['locations'] = data['locations']
        if 'context' in data:
            with Transaction().set_context(data['context']):
                return super(Inventory, cls).execute(ids, data)
        return super(Inventory, cls).execute(ids, data)
