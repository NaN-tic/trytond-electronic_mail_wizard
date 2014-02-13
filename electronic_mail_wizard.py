#This file is part electronic_mail_wizard module for Tryton.
#The COPYRIGHT file at the top level of this repository contains
#the full copyright notices and license terms.
import mimetypes
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email.utils import formatdate
from email import Encoders
from email.header import Header

from trytond.model import ModelView, fields
from trytond.wizard import Wizard, StateTransition, StateView, Button
from trytond.transaction import Transaction
from trytond.pool import Pool
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
    plain = fields.Text('Plain Text Body', required=True)
    total = fields.Integer('Total', readonly=True,
        help='Total emails to send')
    template = fields.Many2One("electronic.mail.template", 'Template')
    model = fields.Many2One(
        'ir.model', 'Model', required=True, select="1")


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
            'template_missing': 'You can select a template in this wizard.',
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
        message['date'] = formatdate(localtime=1)

        language = Transaction().context.get('language', 'en_US')
        if template.language:
            language = Template.eval(template, template.language, record)

        with Transaction().set_context(language=language):
            template = Template(template.id)

            message['from'] = Template.eval(template, values['from_'], record)
            message['to'] = Template.eval(template, values['to'], record)
            message['cc'] = Template.eval(template, values['cc'], record)
            message['bcc'] = Template.eval(template, values['bcc'], record)
            message['subject'] = Header(Template.eval(template,
                    values['subject'], record), 'utf-8')

            # Attach reports
            if template.reports:
                reports = Template.render_reports(
                    template, record
                    )
                for report in reports:
                    ext, data, filename, file_name = report[0:5]
                    if file_name:
                        filename = Template.eval(template, file_name, record)
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

            plain = Template.eval(template, values['plain'], record)
            if template.signature:
                User = Pool().get('res.user')
                user = User(Transaction().user)
                if user.signature:
                    signature = user.signature
                    plain = '%s\n--\n%s' % (
                            plain,
                            signature.encode("utf8"),
                            )
            message.attach(MIMEText(plain, _charset='utf-8'))

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

        wizards = Wizard.search(['wiz_name', '=', name])
        if not len(wizards) > 0:
            return default
        wizard = Wizard(wizards[0])
        if not wizard.template:
            self.raise_user_error('template_missing')
        template = wizard.template[0]
        total = len(active_ids)

        #load data in language when send a record
        if template.language and total == 1:
            record = Pool().get(template.model.model)(active_ids[0])
            language = Template.eval(template, template.language, record)
            with Transaction().set_context(language=language):
                template = Template(template.id)

        default['from_'] = template.from_
        default['total'] = total
        default['template'] = template.id
        default['model'] = template.model.id
        if total > 1:  # show fields with tags
            default['to'] = template.to
            default['cc'] = template.cc
            default['bcc'] = template.bcc
            default['subject'] = template.subject
            default['plain'] = template.plain
        else:  # show fields with rendered tags
            record = Pool().get(template.model.model)(active_ids[0])
            default['to'] = Template.eval(template, template.to, record)
            default['cc'] = Template.eval(template, template.cc, record)
            default['bcc'] = Template.eval(template, template.bcc, record)
            default['subject'] = Template.eval(template, template.subject,
                record)
            default['plain'] = Template.eval(template, template.plain, record)
        return default

    def render_and_send(self):
        template = self.start.template
        #~ model = self.start.model

        for active_id in Transaction().context.get('active_ids'):
            values = {}
            values['from_'] = self.start.from_
            values['to'] = self.start.to
            values['cc'] = self.start.cc
            values['bcc'] = self.start.bcc
            values['subject'] = self.start.subject
            values['plain'] = self.start.plain

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

            email_message = self.render(template, record, values)
            email_id = Email.create_from_email(
                email_message, template.mailbox.id)
            Template.send_email(email_id, template)
            logging.getLogger('Mail').info(
                'Send template email: %s - %s' % (template.name, active_id))

            Pool().get('electronic.mail.template').add_event(template, record,
                email_id, email_message)  # add event
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
        try:
            for template in Template.search([
                        ('wizard', '!=', None),
                        ('create_action', '=', True),
                        ]):
                template.register_electronic_mail_wizard_class()
        except:
            pass
