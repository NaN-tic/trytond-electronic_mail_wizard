# This file is part electronic_mail_wizard module for Tryton.
# The COPYRIGHT file at the top level of this repository contains
# the full copyright notices and license terms.
from trytond.config import config
from trytond.model import ModelView, fields
from trytond.pool import Pool
from trytond.pyson import Eval
from trytond.tools import grouped_slice
from trytond.transaction import Transaction
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.i18n import gettext
from trytond.exceptions import UserError


# Determines max connections to database used for the mail send thread
MAX_DB_CONNECTION = config.getint('database', 'max_connections', default=50)
MAX_ATTACHMENT_SIZE = config.getint('email', 'max_attachment_size',
    default=26214400)


class TemplateEmailAttachment(ModelView):
    'Template Email Attachment'
    __name__ = 'electronic.mail.wizard.templateemail.attachment'

    name = fields.Char('Name')
    data = fields.Binary('Data', filename='name')

    @fields.depends('data')
    def on_change_data(self):
        size = len(self.data or '')
        if size and size >= MAX_ATTACHMENT_SIZE:
            self.data = None
            self.name = None


class TemplateEmailStart(ModelView):
    'Template Email Start'
    __name__ = 'electronic.mail.wizard.templateemail.start'

    from_ = fields.Char('From', readonly=True)
    sender = fields.Char('Sender')
    to = fields.Char('To', required=True)
    cc = fields.Char('CC')
    bcc = fields.Char('BCC')
    use_tmpl_fields = fields.Boolean('Use template fields')
    subject = fields.Char('Subject', required=True,
        states={
            'readonly': Eval('use_tmpl_fields', False),
            })
    plain = fields.Text('Plain Text Body',
        states={
            'readonly': Eval('use_tmpl_fields', False),
            })
    html = fields.Text('HTML Text Body',
        states={
            'readonly': Eval('use_tmpl_fields', False),
            })
    total = fields.Integer('Total', readonly=True,
        help='Total emails to send')
    message_id = fields.Char('Message-ID')
    in_reply_to = fields.Char('In Repply To')
    template = fields.Many2One("electronic.mail.template", 'Template')
    attachments = fields.One2Many(
        'electronic.mail.wizard.templateemail.attachment', None,
        'Attachments', help="Attchments from user computer.")
    origin = fields.Reference('Origin', selection='get_origin')
    origin_attachments = fields.Many2Many('ir.attachment', None, None,
        'Origin Attachments', domain=[
            ('resource', '=', Eval('origin', -1))
                ])

    @staticmethod
    def default_use_tmpl_fields():
        return True

    @classmethod
    def _get_origin(cls):
        pool = Pool()
        Template = pool.get('electronic.mail.template')
        templates = Template.search([])
        return list(set([t.model.model for t in templates]))

    @classmethod
    def get_origin(cls):
        pool = Pool()
        Model = pool.get('ir.model')
        get_name = Model.get_name
        models = cls._get_origin()
        return [(None, '')] + [(m, get_name(m)) for m in models]


class TemplateEmailResult(ModelView):
    'Template Email Result'
    __name__ = 'electronic.mail.wizard.templateemail.result'

    name = fields.Char('Name', help='Name of Header Field')


class GenerateTemplateEmail(Wizard):
    "Generate Email from template"
    __name__ = "electronic_mail_wizard.templateemail"

    start = StateView('electronic.mail.wizard.templateemail.start',
        'electronic_mail_wizard.templateemail_start', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Send', 'send', 'tryton-ok'),
            ])
    send = StateTransition()

    def default_start(self, fields):
        pool = Pool()
        Wizard = pool.get('ir.action.wizard')
        context = Transaction().context
        active_ids = context.get('active_ids', [])
        if not active_ids:
            return {}

        default = self.render_fields(self.__name__)
        if len(active_ids) >= 2:
            default['use_tmpl_fields'] = True
        else:
            action_id = context.get('action_id', None)
            wizard = Wizard(action_id)
            template = wizard.template[0] if wizard.template else None
            if not template:
                raise UserError(gettext(
                    'electronic_mail_wizard.template_deleted'))

            default['use_tmpl_fields'] = False
            default['origin'] = "%s,%s" % (template.model.model, active_ids[0])
        return default

    def transition_send(self):
        context = Transaction().context
        active_ids = context.get('active_ids', [])
        if not active_ids:
            return 'end'

        self.render_and_send()
        return 'end'

    def render_fields(self, name):
        '''Get the fields before render and return a dicc
        :param name: Str ir.action.wizard
        :return: dicc
        '''
        pool = Pool()
        Wizard = pool.get('ir.action.wizard')
        Template = pool.get('electronic.mail.template')

        context = Transaction().context
        active_ids = context.get('active_ids')
        action_id = context.get('action_id', None)
        wizard = Wizard(action_id)
        template = wizard.template[0] if wizard.template else None
        if not template:
            raise UserError(gettext(
                'electronic_mail_wizard.template_deleted'))
        total = len(active_ids)

        record = pool.get(template.model.name)(active_ids[0])
        # load data in language when send a record
        if template.language:
            language = template.eval(template.language, record)
        else:
            language = Transaction().context.get('language')

        with Transaction().set_context(language=language):
            template = Template(template.id)

            default = {}
            default['template'] = template.id
            default['total'] = total
            if total > 1:  # show fields with tags
                default['from_'] = template.from_
                default['message_id'] = template.message_id
                if template.in_reply_to:
                    default['in_reply_to'] = template.in_reply_to
                if template.sender:
                    default['sender'] = template.sender
                default['to'] = template.to
                if template.cc:
                    default['cc'] = template.cc
                if template.bcc:
                    default['bcc'] = template.bcc
                default['subject'] = template.subject
                default['plain'] = template.plain
                default['html'] = template.html
            else:
                # Show fields with rendered tags and using template's language
                record = pool.get(template.model.name)(active_ids[0])
                default['from_'] = template.eval(template.from_, record)
                default['message_id'] = template.eval(template.message_id, record)
                if template.in_reply_to:
                    default['in_reply_to'] = template.eval(template.in_reply_to,
                        record)
                if template.sender:
                    default['sender'] = template.eval(template.sender, record)
                default['to'] = template.eval(template.to, record)
                if template.cc:
                    default['cc'] = template.eval(template.cc, record)
                if template.bcc:
                    default['bcc'] = template.eval(template.bcc, record)
                default['subject'] = template.eval(template.subject, record)
                default['plain'] = template.eval(template.plain, record)
                default['html'] = template.eval(template.html, record)
        return default

    def render_and_send(self):
        pool = Pool()
        Template = pool.get('electronic.mail.template')
        ElectronicEmail = pool.get('electronic.mail')

        template = self.start.template
        if not template:
            raise UserError(gettext(
                'electronic_mail_wizard.template_deleted'))

        records = Transaction().context.get('active_ids')
        for sub_records in grouped_slice(records, MAX_DB_CONNECTION):
            for active_id in sub_records:
                record = pool.get(template.model.name)(active_id)
                # load data in language when send a record
                if template.language:
                    language = template.eval(template.language, record)
                else:
                    language = Transaction().context.get('language')

                with Transaction().set_context(language=language):
                    template = Template(template.id)
                values = {
                    'from_': self.start.from_,
                    'sender': self.start.sender,
                    'to': self.start.to,
                    'cc': self.start.cc,
                    'bcc': self.start.bcc,
                    'message_id': self.start.message_id,
                    'in_reply_to': self.start.in_reply_to,
                    'template': template.id,
                    }
                if self.start.use_tmpl_fields:
                    tmpl_fields = ('subject', 'plain', 'html')
                    for field_name in tmpl_fields:
                        values[field_name] = getattr(template, field_name)
                else:
                    values.update({
                        'subject': self.start.subject,
                        'plain': self.start.plain,
                        'html': self.start.html,
                        })

                attachments = []
                for attachment in (self.start.attachments
                        + self.start.origin_attachments):
                    if attachment.data:
                        attachments.append({
                            'name': attachment.name,
                            'data': attachment.data,
                            })

                with Transaction().set_context(language=language):
                    mail_message = Template.render(template, record, values,
                        extra_attachments=attachments)

                electronic_mail = ElectronicEmail.create_from_mail(mail_message,
                    template.mailbox.id, record)
                if not electronic_mail:
                    continue
                electronic_mail.template = template
                electronic_mail.save()

                # call send_mail button. _send_mail is the queue
                ElectronicEmail.send_mail([electronic_mail])
