#This file is part electronic_mail_wizard module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.utils import formatdate, make_msgid
from email import Encoders
from email.header import Header

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.transaction import Transaction
from trytond.pool import Pool
from trytond import backend
import threading
import logging

__all__ = ['TemplateEmailStart', 'TemplateEmailResult',
    'GenerateTemplateEmail', 'VirtualGenerateTemplateEmail']


class TemplateEmailStart(ModelView):
    'Template Email Start'
    __name__ = 'electronic.mail.wizard.templateemail.start'

    from_ = fields.Char('From', readonly=True)
    sender = fields.Char('Sender', required=True)
    to = fields.Char('To', required=True)
    cc = fields.Char('CC')
    bcc = fields.Char('BCC')
    subject = fields.Char('Subject', required=True)
    plain = fields.Text('Plain Text Body')
    html = fields.Text('HTML Text Body')
    total = fields.Integer('Total', readonly=True,
        help='Total emails to send')
    message_id = fields.Char('Message-ID')
    in_reply_to = fields.Char('In Repply To')
    template = fields.Many2One("electronic.mail.template", 'Template')


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

    def render(self, template, record, values):
        '''Renders the template and returns as email object
        :param template: Object of the template
        :param record: Object of the template
        :param values: Dicctionary values
        :return: 'email.message.Message' instance
        '''
        Template = Pool().get('electronic.mail.template')

        message = MIMEMultipart()
        messageid = template.eval(values['message_id'], record)
        message['Message-Id'] = messageid or make_msgid()
        message['Date'] = formatdate(localtime=1)
        if values.get('in_reply_to'):
            message['In-Reply-To'] = template.eval(values['in_reply_to'],
                record)

        language = Transaction().context.get('language', 'en_US')
        if template.language:
            language = template.eval(template.language, record)

        with Transaction().set_context(language=language):
            template = Template(template.id)

            message['From'] = template.eval(values['from_'], record)
            message['To'] = template.eval(values['to'], record)
            if values.get('cc'):
                message['Cc'] = template.eval(values['cc'], record)
            if values.get('bcc'):
                message['Bcc'] = template.eval(values['bcc'], record)
            message['Subject'] = Header(template.eval(values['subject'],
                    record), 'utf-8')

            plain = template.eval(values['plain'], record)
            html = template.eval(values['html'], record)
            header = """
                <html>
                <head><head>
                <body>
                """
            footer = """
                </body>
                </html>
                """
            if html:
                html = "%s%s" % (header, html)
            if template.signature:
                User = Pool().get('res.user')
                user = User(Transaction().user)
                if html and user.signature_html:
                    signature = user.signature_html.encode('utf8')
                    html = '%s<br>--<br>%s' % (html, signature)
                if plain and user.signature:
                    signature = user.signature.encode('utf-8')
                    plain = '%s\n--\n%s' % (plain, signature)
                    if html and not user.signature_html:
                        html = '%s<br>--<br>%s' % (html.encode('utf-8'),
                            signature.replace('\n', '<br>'))
            if html:
            	html = "%s%s" % (html, footer)
            body = None
            if html and plain:
                body = MIMEMultipart('alternative')
            if plain:
                if body:
            	    body.attach(MIMEText(plain, 'plain', _charset='utf-8'))
                else:
            	    message.attach(MIMEText(plain, 'plain', _charset='utf-8'))
            if html:
                if body:
            	    body.attach(MIMEText(html, 'html', _charset='utf-8'))
                else:
            	    message.attach(MIMEText(html, 'html', _charset='utf-8'))
            if body:
                message.attach(body)

            # Attach reports
            if template.reports:
                reports = Template.render_reports(template, record)
                for report in reports:
                    ext, data, filename, file_name = report[0:5]
                    if file_name:
                        filename = template.eval(file_name, record)
                    filename = ext and '%s.%s' % (filename, ext) or filename
                    content_type, _ = mimetypes.guess_type(filename)
                    maintype, subtype = (
                        content_type or 'application/octet-stream'
                        ).split('/', 1)

                    attachment = MIMEBase(maintype, subtype)
                    attachment.set_payload(data)
                    Encoders.encode_base64(attachment)
                    attachment.add_header(
                        'Content-Disposition', 'attachment', filename=filename)
                    attachment.add_header(
                        'Content-Transfer-Encoding', 'base64')
                    message.attach(attachment)

        return message

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
        if template.language and total == 1:
            language = template.eval(template.language, record)
            with Transaction().set_context(language=language):
                template = Template(template.id)

        default['from_'] = template.eval(template.from_, record)
        default['total'] = total
        default['template'] = template.id
        if total > 1:  # show fields with tags
            default['message_id'] = template.message_id
            if template.in_reply_to:
                default['in_reply_to'] = template.in_reply_to
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
        Mail = pool.get('electronic.mail')

        template = self.start.template

        for active_id in Transaction().context.get('active_ids'):
            record = pool.get(template.model.model)(active_id)
            values = {}
            values['message_id'] = self.start.message_id
            if self.start.in_reply_to:
                values['in_reply_to'] = self.start.in_reply_to
            values['from_'] = self.start.from_
            values['to'] = self.start.to
            if self.start.cc:
                values['cc'] = self.start.cc
            if self.start.bcc:
                values['bcc'] = self.start.bcc
            values['subject'] = self.start.subject
            values['plain'] = self.start.plain
            values['html'] = self.start.html

            emails = []
            if self.start.from_:
                emails += template.eval(self.start.from_, record).split(',')
            if self.start.to:
                emails += template.eval(self.start.to, record).split(',')
            if self.start.cc:
                emails += template.eval(self.start.cc, record).split(',')
            if self.start.bcc:
                emails += template.eval(self.start.bcc, record).split(',')

            Mail.validate_emails(emails)

            db_name = Transaction().cursor.dbname
            thread1 = threading.Thread(target=self.render_and_send_thread,
                args=(db_name, Transaction().user, template, active_id,
                    values,))
            thread1.start()

    def render_and_send_thread(self, db_name, user, template, active_id,
            values):
        with Transaction().start(db_name, user) as transaction:
            pool = Pool()
            Email = pool.get('electronic.mail')
            Template = pool.get('electronic.mail.template')

            template, = Template.browse([template])
            record = Pool().get(template.model.model)(active_id)

            mail_message = self.render(template, record, values)

            electronic_mail = Email.create_from_mail(mail_message,
                template.mailbox.id)
            Template.send_mail(electronic_mail, template)
            logging.getLogger('Mail').info(
                'Send template email: %s - %s' % (template.name, active_id))

            Pool().get('electronic.mail.template').add_event(template, record,
                electronic_mail, mail_message)  # add event
            transaction.cursor.commit()


class VirtualGenerateTemplateEmail(GenerateTemplateEmail):
    "Virtual Wizard to Generate Email from template"
    __name__ = "electronic_mail_wizard.virtual"

    @classmethod
    def __post_setup__(cls):
        pool = Pool()
        Template = pool.get('electronic.mail.template')
        super(VirtualGenerateTemplateEmail, cls).__post_setup__()
        #Register all wizard without class
        TableHandler = backend.get('TableHandler')
        table = TableHandler(Transaction().cursor, Template,
            'electronic_mail_wizard')
        if table.column_exist('create_action'):
            for template in Template.search([
                        ('create_action', '=', True),
                        ]):
                template.register_electronic_mail_wizard_class()
