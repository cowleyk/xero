import json
from xero import Xero
from xero.auth import PrivateCredentials

from nio import Block
from nio.signal.base import Signal
from nio.properties import VersionProperty, ObjectProperty, StringProperty, \
    PropertyHolder, FloatProperty, IntProperty, ListProperty, Property


class JournalLines(PropertyHolder):
    line_amount = Property(default='{{ $amount }}', title='Line Amount')
    account_code = Property(default=100, title='Account Code')
    line_description = Property(default='Description', title='Description')


class ManualJournals(PropertyHolder):
    narration = StringProperty(default='Narration', title="Narration")
    journal_lines = ListProperty(JournalLines, title='Journal Lines', default=[])



class XeroUpdate(Block):

    version = VersionProperty('0.1.0')
    consumer_key = StringProperty(title='Xero Consumer Key',
                                  default='[[XERO_CONSUMER_KEY]]',
                                  allow_none=False)
    manual_journal_entries = ListProperty(ManualJournals,
                                          title='Manual Journal Entries',
                                          default=[])
    contact_name = StringProperty(title='Contact Name (Stripe customerID)',
                                  default='{{ $customer }}')
    description = StringProperty(title='Transaction Description',
                                 default='Description')
    payment_amount = FloatProperty(title='Amount Paid',
                                   default='{{ $amount }}')
    invoice_account_code = IntProperty(title='Invoice Account Code',
                                       default=310)

    def __init__(self):
        self.xero = None
        self.credentials = None
        super().__init__()

    def configure(self, context):
        super().configure(context)

        con_key = self.consumer_key()
        with open('blocks/xero/privatekey.pem') as keyfile:
            rsa_private_key = keyfile.read()

        self.credentials = PrivateCredentials(con_key, rsa_private_key)
        self.xero = Xero(self.credentials)

    def start(self):
        super().start()

    def process_signals(self, signals):
        response_signal = []
        for signal in signals:
            invoice_resp_signal = self.xero.invoices.filter(
                Contact_Name=self.contact_name(signal),
                Status='AUTHORISED',
                order='UpdatedDateUTC DESC')[0]

            invoice_id = invoice_resp_signal['InvoiceID']
            invoice_subtotal = invoice_resp_signal['SubTotal']
            invoice_tax = invoice_resp_signal['TotalTax']
            invoice_total = invoice_resp_signal['Total']

            response_signal.append(Signal(self.xero.payments.put({
                'Invoice': {
                    'InvoiceID': invoice_id
                },
                'Account': {
                    'Code': self.invoice_account_code()
                },
                'Amount': self.payment_amount(signal)
            })[0]))

            for man_jour in self.manual_journal_entries():
                line_items_list = []
                for jour_line in man_jour.journal_lines():
                    line_items_list.append({
                        'Description': jour_line.line_description(),
                        'LineAmount': jour_line.line_amount(signal),
                        'AccountCode': jour_line.account_code()
                    })
                response_signal.append(Signal(self.xero.manualjournals.put({
                    'Narration': man_jour.narration(),
                    'JournalLines': line_items_list
                })[0]))




        self.notify_signals(response_signal)
