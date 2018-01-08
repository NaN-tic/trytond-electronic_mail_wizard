# This file is part electronic_mail_wizard module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
try:
    from trytond.modules.electronic_mail_wizard.tests.test_electronic_mail_wizard import (
        suite)
except ImportError:
    from .test_electronic_mail_wizard import suite

__all__ = ['suite']
