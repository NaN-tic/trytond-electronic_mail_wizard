# This file is part electronic_mail_wizard module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from . import electronic_mail_wizard
from . import template
from . import action


def register():
    Pool.register(
        electronic_mail_wizard.TemplateEmailStart,
        electronic_mail_wizard.TemplateEmailResult,
        action.ActionWizard,
        template.Template,
        module='electronic_mail_wizard', type_='model')
    Pool.register(
        electronic_mail_wizard.GenerateTemplateEmail,
        module='electronic_mail_wizard', type_='wizard')
