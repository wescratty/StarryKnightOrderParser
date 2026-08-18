"""
utility_modules package.

Exposes the two small convenience aliases StarryKnightOrderParser.py
actually uses (fh = FileHelper, stk = SuperTk), plus the orderItem
submodule itself (StarryKnightOrderParser.py calls
utility_modules.orderItem.parse_orders() directly rather than importing
a name for it).
"""

from .tkinterface import SuperTk as stk
from .fileHelper import FileHelper as fh
from . import orderItem
