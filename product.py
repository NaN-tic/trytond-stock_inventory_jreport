# This file is part of stock_inventory_jasper module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
from trytond.pool import PoolMeta
from trytond.model import fields

__all__ = ['Product']


class Product(metaclass=PoolMeta):
    __name__ = "product.product"
    inventory_cost_value = fields.Function(fields.Numeric(
        'Inventory Cost Value'), 'get_inventory_cost_value')

    @classmethod
    def get_inventory_cost_value(cls, products, name):
        return cls.get_cost_value(products, name)
