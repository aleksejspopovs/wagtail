import datetime

version = 1

def _pretty_print_principal(principal):
    if principal.endswith('@ATHENA.MIT.EDU'):
        return principal[:-len('@ATHENA.MIT.EDU')]
    return principal

def _format_date(unix_time):
    date = datetime.datetime.fromtimestamp(unix_time)
    return date.strftime('%Y-%m-%d %H:%M')

def get_zgram_display_properties(zgram, is_current):
    properties = {}

    # header
    auth = '' if zgram.auth else '!'
    opcode = ' [{}]'.format(zgram.opcode) if zgram.opcode else ''
    zsig = ' ({})'.format(zgram.fields[0]) if len(zgram.fields) > 0 else ''
    date = _format_date(zgram.time or 0)
    sender = _pretty_print_principal(zgram.sender) if zgram.sender else ''
    recipient = _pretty_print_principal(zgram.recipient)

    format = ''
    if zgram.cls.lower() == 'message':
        format = '→{recipient} from {auth}{sender}{opcode} {date}{zsig}'
    else:
        format = '{class_} / {instance} / {auth}{sender}{opcode} {date}{zsig}'

    properties['header'] = format.format(
        class_=zgram.cls,
        instance=zgram.instance,
        recipient=recipient,
        auth=auth,
        sender=sender,
        opcode=opcode,
        date=date,
        zsig=zsig)

    # coloring
    if zgram.cls.lower() == 'message':
        properties['bg_color'] = 'magenta'

    return properties

def compute_zsig(sender, class_, instance, recipients, opcode, auth, body):
    return 'sent from wagtail'
