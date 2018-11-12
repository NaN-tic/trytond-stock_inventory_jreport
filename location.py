# This file is part of Tryton.  The COPYRIGHT file at the top level of
# this repository contains the full copyright notices and license terms.
from trytond.pool import PoolMeta

__all__ = ['Location']


class Location(metaclass=PoolMeta):
    __name__ = 'stock.location'

    def report_title(self):
        if self.code:
            return ("%s [%s]" % (self.name.strip(), self.code.strip()))
        return ("%s" % (self.name.strip()))
