import datetime

version = 1

def _pretty_print_principal(principal):
    if principal.endswith('@ATHENA.MIT.EDU'):
        return principal[:-len('@ATHENA.MIT.EDU')]
    return principal

def _format_date(date):
    return date.strftime('%Y-%m-%d %H:%M')

def get_zgram_display_properties(zgram, is_current):
    properties = {}

    # header
    auth = '' if zgram.auth else '!'
    opcode = ' [{}]'.format(zgram.opcode) if zgram.opcode else ''
    zsig = ' ({})'.format(zgram.signature) if len(zgram.signature) > 0 else ''
    date = _format_date(zgram.time)
    sender = _pretty_print_principal(zgram.sender) if zgram.sender else ''
    recipient = _pretty_print_principal(zgram.recipient)

    format = ''
    if zgram.is_personal():
        format = '→{recipient} from {auth}{sender}{opcode} {date}{zsig}'
    else:
        format = '{class_} / {instance} / {auth}{sender}{opcode} {date}{zsig}'

    properties['header'] = format.format(
        class_=zgram.class_,
        instance=zgram.instance,
        recipient=recipient,
        auth=auth,
        sender=sender,
        opcode=opcode,
        date=date,
        zsig=zsig)

    # coloring
    if zgram.is_personal():
        properties['bg_color'] = 'magenta'

    return properties

def compute_zsig(sender, class_, instance, recipients, opcode, auth, body):
    return 'sent from wagtail'
