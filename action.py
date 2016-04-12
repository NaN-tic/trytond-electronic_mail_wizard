# This file is part electronic_mail_wizard module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import PoolMeta

__all__ = ['ActionWizard']


class ActionWizard:
    __name__ = 'ir.action.wizard'
    __metaclass__ = PoolMeta
    template = fields.One2Many("electronic.mail.template", 'wizard',
        'Template')
