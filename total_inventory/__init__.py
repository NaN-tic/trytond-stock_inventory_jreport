from trytond.pool import Pool
from . import total_inventory

def register(module):
    Pool.register(
        total_inventory.PrintTotalInventoryStart,
        module=module, type_='model')
    Pool.register(
        total_inventory.PrintTotalInventory,
        module=module, type_='wizard')
    Pool.register(
        total_inventory.TotalInventoryReport,
        module=module, type_='report')