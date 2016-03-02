#This file is part electronic_mail_wizard module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.utils import formatdate, make_msgid
from email import Encoders, charset

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.transaction import Transaction
from trytond.pyson import Eval
from trytond.pool import Pool
from trytond.config import config
from trytond.tools import grouped_slice
import threading
import logging

__all__ = ['TemplateEmailStart', 'TemplateEmailResult',
    'GenerateTemplateEmail']


# Determines max connections to database used for the mail send thread
MAX_DB_CONNECTION = config.getint('database', 'max_connections', 50)


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
            },
        depends=['use_tmpl_fields'])
    plain = fields.Text('Plain Text Body',
        states={
            'readonly': Eval('use_tmpl_fields', False),
            },
        depends=['use_tmpl_fields'])
    html = fields.Text('HTML Text Body',
        states={
            'readonly': Eval('use_tmpl_fields', False),
            },
        depends=['use_tmpl_fields'])
    total = fields.Integer('Total', readonly=True,
        help='Total emails to send')
    message_id = fields.Char('Message-ID')
    in_reply_to = fields.Char('In Repply To')
    template = fields.Many2One("electronic.mail.template", 'Template')

    @staticmethod
    def default_use_tmpl_fields():
        return True


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
            Button('Send', 'send', 'tryton-ok', default=True),
            ])
    send = StateTransition()

    @classmethod
    def __setup__(cls):
        super(GenerateTemplateEmail, cls).__setup__()
        cls._error_messages.update({
            'template_deleted': 'This template has been deactivated or '
                'deleted.',
            })

    def default_start(self, fields):
        default = self.render_fields(self.__name__)
        return default

    def transition_send(self):
        self.render_and_send()
        return 'end'

    def render_fields(self, name):
        '''Get the fields before render and return a dicc
        :param name: Str ir.action.wizard
        :return: dicc
        '''
        default = {}

        Wizard = Pool().get('ir.action.wizard')
        Template = Pool().get('electronic.mail.template')
        active_ids = Transaction().context.get('active_ids')

        context = Transaction().context
        action_id = context.get('action_id', None)
        wizard = Wizard(action_id)
        template = (wizard.template and wizard.template[0]
            or self.raise_user_error('template_deleted'))
        total = len(active_ids)

        record = Pool().get(template.model.model)(active_ids[0])
        #load data in language when send a record
        if template.language:
            language = template.eval(template.language, record)
            with Transaction().set_context(language=language):
                template = Template(template.id)

        default['template'] = template.id
        default['from_'] = template.eval(template.from_, record)
        default['total'] = total
        if total > 1:  # show fields with tags
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
        else:  # show fields with rendered tags
            record = Pool().get(template.model.model)(active_ids[0])
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
            default['subject'] = template.eval(template.subject,
                record)
            default['plain'] = template.eval(template.plain, record)
            default['html'] = template.eval(template.html, record)
        return default

    def render_and_send(self):
        pool = Pool()
        Template = pool.get('electronic.mail.template')

        template = self.start.template

        records = Transaction().context.get('active_ids')
        for sub_records in grouped_slice(records, MAX_DB_CONNECTION):
            threads = []
            for active_id in sub_records:
                record = pool.get(template.model.model)(active_id)
                #load data in language when send a record
                if template.language:
                    language = template.eval(template.language, record)
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

                db_name = Transaction().cursor.dbname
                thread1 = threading.Thread(target=self.render_and_send_thread,
                    args=(db_name, Transaction().user, template, active_id,
                        values,))
                threads.append(thread1)
                thread1.start()
            for thread in threads:
                thread.join()

    def render_and_send_thread(self, db_name, user, template, active_id,
            values):
        with Transaction().start(db_name, user) as transaction:
            pool = Pool()
            Email = pool.get('electronic.mail')
            Template = pool.get('electronic.mail.template')

            template, = Template.browse([template])
            record = pool.get(template.model.model)(active_id)

            mail_message = Template.render(template, record, values)

            electronic_mail = Email.create_from_mail(mail_message,
                template.mailbox.id)
            Template.send_mail(electronic_mail, template)
            logging.getLogger('Mail').info(
                'Send template email: %s - %s' % (template.name, active_id))

            Pool().get('electronic.mail.template').add_event(template, record,
                electronic_mail, mail_message)  # add event
            transaction.cursor.commit()
