# This file is part electronic_mail_wizard module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.pool import Pool
from .electronic_mail_wizard import *
from .template import *
from .action import *


def register():
    Pool.register(
        TemplateEmailStart,
        TemplateEmailResult,
        ActionWizard,
        Template,
        module='electronic_mail_wizard', type_='model')
    Pool.register(
        GenerateTemplateEmail,
        module='electronic_mail_wizard', type_='wizard')
