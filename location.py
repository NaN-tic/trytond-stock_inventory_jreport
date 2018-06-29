# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
import datetime
from trytond.wizard import StateAction, Button
from trytond.transaction import Transaction
from trytond.pool import PoolMeta, Pool

__all__ = ['Location']


class Location:
    __metaclass__ = PoolMeta
    __name__ = 'stock.location'

    def report_title(self):
        if self.code:
            return ("%s [%s]" % (self.name.strip(), self.code.strip()))
        return ("%s" % (self.name.strip()))
