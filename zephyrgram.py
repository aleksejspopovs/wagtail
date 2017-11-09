from datetime import datetime

from zpipe.python.zpipe import Zephyrgram as ZpipeZephyrgram

class Zephyrgram:
    def __init__(self, rowid, sender, class_, instance, recipient, opcode, auth,
        time, signature, body):
        self.rowid = rowid
        self.sender = sender
        self.class_ = class_
        self.instance = instance
        self.recipient = recipient
        self.opcode = opcode
        self.auth = auth
        self.time = time
        self.signature = signature
        self.body = body

    @classmethod
    def from_zpipe(cls, zpipe_zephyrgram):
        time = datetime.fromtimestamp(zpipe_zephyrgram.time)

        signature = ''
        if len(zpipe_zephyrgram.fields) >= 1:
            signature = zpipe_zephyrgram.fields[0]

        body = ''
        if len(zpipe_zephyrgram.fields) >= 2:
            body = zpipe_zephyrgram.fields[1]

        return cls(rowid=None,
            sender=zpipe_zephyrgram.sender,
            class_=zpipe_zephyrgram.cls,
            instance=zpipe_zephyrgram.instance,
            recipient=zpipe_zephyrgram.recipient,
            opcode=zpipe_zephyrgram.opcode,
            auth=zpipe_zephyrgram.auth,
            time=time,
            signature=signature,
            body=body)

    def to_zpipe(self):
        fields = [self.signature, self.body]
        unix_time = None
        if self.time is not None:
            unix_time = self.time.timestamp()

        return ZpipeZephyrgram(sender=self.sender,
            cls=self.class_,
            instance=self.instance,
            recipient=self.recipient,
            opcode=self.opcode,
            auth=self.auth,
            fields=fields,
            time=unix_time)

    @classmethod
    def from_sql(cls, row):
        return cls(rowid=row['id'],
            sender=row['sender'],
            class_=row['class'],
            instance=row['instance'],
            recipient=row['recipient'],
            opcode=row['opcode'],
            auth=row['auth'],
            time=row['time'],
            signature=row['signature'],
            body=row['body'])

    def to_sql(self):
        return {
            'id': self.rowid,
            'sender': self.sender,
            'class': self.class_,
            'instance': self.instance,
            'recipient': self.recipient,
            'opcode': self.opcode,
            'auth': self.auth,
            'time': self.time,
            'signature': self.signature,
            'body': self.body
        }

    def is_personal(self):
        return self.class_.lower() == 'message'

