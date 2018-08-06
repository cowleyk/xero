from xero import Xero
from xero.auth import PrivateCredentials

from nio import Block
from nio.signal.base import Signal
from nio.properties import (VersionProperty, StringProperty, FloatProperty,
                            IntProperty)


class XeroUpdateInvoice(Block):

    version = VersionProperty("0.1.3")
    consumer_key = StringProperty(title='Xero Consumer Key',
                                  default='[[XERO_CONSUMER_KEY]]',
                                  allow_none=False)
    contact_name = StringProperty(title='Contact Name (Stripe customerID)',
                                  default='{{ $customer }}')
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
        with open('blocks/xero/keys/privatekey.pem') as keyfile:
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

            response_signal.append(Signal(self.xero.payments.put({
                'Invoice': {
                    'InvoiceID': invoice_id
                },
                'Account': {
                    'Code': self.invoice_account_code()
                },
                'Amount': self.payment_amount(signal)
            })[0]))

        self.notify_signals(response_signal)
