import datetime

version = 1

def _pretty_print_principal(principal):
    if principal.endswith('@ATHENA.MIT.EDU'):
        return principal[:-len('@ATHENA.MIT.EDU')]
    return principal

def _format_date(unix_time):
    date = datetime.datetime.fromtimestamp(unix_time)
    return date.strftime('%Y-%m-%d %H:%M')

def format_zgram_header(zgram):
    auth = '' if zgram.auth else '!'
    zsig = ' ({})'.format(zgram.fields[0]) if len(zgram.fields) > 0 else ''
    date = _format_date(zgram.time or 0)
    sender = _pretty_print_principal(zgram.sender) if zgram.sender else ''
    recipient = _pretty_print_principal(zgram.recipient)

    format = ''
    if zgram.cls.lower() == 'message':
        format = '→{recipient} from {auth}{sender} {date}{zsig}'
    else:
        format = '{class_} / {instance} / {auth}{sender} {date}{zsig}'

    return format.format(
            class_=zgram.cls,
            instance=zgram.instance,
            recipient=recipient,
            auth=auth,
            sender=sender,
            date=date,
            zsig=zsig)

def compute_zsig(class_, instance, recipients, opcode, auth, body):
    return 'sent from wagtail'
