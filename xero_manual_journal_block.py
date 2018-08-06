from xero import Xero
from xero.auth import PrivateCredentials

from nio.block.base import Block
from nio.signal.base import Signal
from nio.properties import (StringProperty, PropertyHolder, Property,
                            ListProperty, VersionProperty)


class JournalLines(PropertyHolder):
    line_amount = Property(default='{{ $amount }}', title='Line Amount')
    account_code = Property(default=100, title='Account Code')
    line_description = Property(default='Description', title='Description')


class ManualJournals(PropertyHolder):
    narration = StringProperty(default='Narration', title="Narration")
    journal_lines = ListProperty(JournalLines, title='Journal Lines', default=[])


class XeroManualJournals(Block):
    manual_journal_entries = ListProperty(ManualJournals,
                                          title='Manual Journal Entries',
                                          default=[])
    version = VersionProperty("0.1.3")
    consumer_key = StringProperty(title='Xero Consumer Key',
                                  default='[[XERO_CONSUMER_KEY]]',
                                  allow_none=False)

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

            for man_jour in self.manual_journal_entries():
                line_items_list = []
                for jour_line in man_jour.journal_lines():
                    line_items_list.append({
                        'Description': jour_line.line_description(),
                        'LineAmount': jour_line.line_amount(signal),
                        'AccountCode': jour_line.account_code()
                    })
                response_signal.append(Signal(self.xero.manualjournals.put({
                    'Narration': man_jour.narration(signal),
                    'Status': 'POSTED',
                    'JournalLines': line_items_list
                })[0]))
