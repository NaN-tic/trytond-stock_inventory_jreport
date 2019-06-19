# This file is part of stock_inventory_jreport module for Tryton.
# The COPYRIGHT file at the top level of this repository contains the full
# copyright notices and license terms.
import datetime
from trytond.modules.jasper_reports.jasper import JasperReport
from trytond.transaction import Transaction
from trytond.pool import Pool


__all__ = ['InventoryReport', 'BlindCountReport', 'InventoryValuedReport']


class InventoryReport(JasperReport):
    __name__ = 'stock.inventory.jreport'


class BlindCountReport(JasperReport):
    __name__ = 'stock.blind_count.jreport'


class InventoryValuedReport(JasperReport):
    __name__ = 'stock.inventory.valued.jreport'

    @classmethod
    def execute(cls, ids, data):
        Location = Pool().get('stock.location')

        context = Transaction().context
        stock_date_end = context.get('stock_date_end', datetime.date.today())
        locale = context.get('locale')
        if locale:
            dformat = locale['date']
        else:
            dformat = '%Y/%m/%d'

        if 'parameters' not in data:
            data['parameters'] = {}
        data['parameters']['stock_date_end'] = stock_date_end.strftime(dformat)
        if 'locations' in data:
            data['parameters']['locations'] = data['locations']
        elif context.get('locations'):
            locations = Location.browse(context.get('locations'))
            data['parameters']['locations'] = ' / '.join(
                [l.report_title() for l in locations])
        if 'context' in data:
            with Transaction().set_context(data['context']):
                return super(InventoryValuedReport, cls).execute(ids, data)
        return super(InventoryValuedReport, cls).execute(ids, data)
