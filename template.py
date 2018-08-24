# This file is part electronic_mail_wizard module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.model import fields
from trytond.pool import Pool, PoolMeta
from trytond.pyson import Eval
from trytond.transaction import Transaction

__all__ = ['Template']


class Template(metaclass=PoolMeta):
    __name__ = 'electronic.mail.template'
    create_action = fields.Boolean('Create Action', help='If set a wizard '
        'action will be created in the related model in order to send the '
        'template.')
    wizard = fields.Many2One("ir.action.wizard", 'Wizard',
        states={
            'readonly': Eval('create_action', False),
            },
        depends=['create_action'])

    @classmethod
    def __register__(cls, module_name):
        Wizard = Pool().get('ir.action.wizard')
        wizard = Wizard.__table__()

        super(Template, cls).__register__(module_name)

        # Migration from 3.4: update wiz_name field with generic value
        cursor = Transaction().connection.cursor()
        cursor.execute(*wizard.select(wizard.id, where=wizard.wiz_name.like(
                    'electronic_mail_wizard.templateemail_%')))
        if cursor.fetchone():
            cursor.execute(*wizard.update([wizard.wiz_name],
                    ['electronic_mail_wizard.templateemail'],
                    where=wizard.wiz_name.like(
                        'electronic_mail_wizard.templateemail_%')))

    @staticmethod
    def default_create_action():
        return True

    @classmethod
    def create(cls, vlist):
        templates = super(Template, cls).create(vlist)
        cls.create_wizards(templates)
        return templates

    @classmethod
    def write(cls, *args):
        pool = Pool()
        Wizard = pool.get('ir.action.wizard')
        super(Template, cls).write(*args)
        actions = iter(args)
        for templates, values in zip(actions, actions):
            if 'create_action' in values:
                if values['create_action']:
                    cls.create_wizards(templates)
                else:
                    cls.delete_wizards(templates)
            if values.get('name'):
                wizards = [t.wizard for t in templates if t.wizard]
                if wizards:
                    Wizard.write(wizards, {
                            'name': values.get('name'),
                            })

    @classmethod
    def delete(cls, templates):
        cls.delete_wizards(templates, ensure_create_action=False)
        super(Template, cls).delete(templates)

    @classmethod
    def create_wizards(cls, templates):
        pool = Pool()
        Keyword = pool.get('ir.action.keyword')
        Wizard = pool.get('ir.action.wizard')
        Lang = pool.get('ir.lang')
        langs = Lang.search([
            ('translatable', '=', True),
            ])
        for template in templates:
            if not template.create_action:
                continue
            wizard = Wizard()
            wizard.name = template.name
            wizard.wiz_name = 'electronic_mail_wizard.templateemail'
            wizard.save()
            template.wizard = wizard
            template.save()

            if langs:
                for lang in langs:
                    with Transaction().set_context(language=lang.code,
                            fuzzy_translation=False):
                        lang_name, = cls.read([template.id], ['name'])
                        Wizard.write([wizard], lang_name)

            keyword = Keyword()
            keyword.keyword = 'form_action'
            keyword.action = wizard.action
            keyword.model = '%s,-1' % template.model.model
            keyword.save()

    @classmethod
    def delete_wizards(cls, templates, ensure_create_action=True):
        pool = Pool()
        Keyword = pool.get('ir.action.keyword')
        Wizard = pool.get('ir.action.wizard')
        wizards = [t.wizard for t in templates if t.wizard
            and (not ensure_create_action or not t.create_action)]
        if wizards:
            keywords = Keyword.search([
                    ('action', 'in', [w.action for w in wizards]),
                    ])
            if keywords:
                Keyword.delete(keywords)
            Wizard.delete(wizards)
