import os
import pwd
import subprocess

def get_principal():
    if os.getenv('WAGTAIL_PRINCIPAL'):
        return os.getenv('WAGTAIL_PRINCIPAL')

    # try getting the principal from Kerberos by running klist
    try:
        result = subprocess.run(('klist', ), stdout=subprocess.PIPE)
    except FileNotFoundError:
        pass
    else:
        lines = result.stdout.decode('utf-8').split('\n')
        if (len(lines) >= 2) and (lines[1].startswith('Default principal: ')):
            return lines[1][len('Default principal: '):]

    # if that fails (klist not found, no tickets, ...)
    default_realm = 'ATHENA.MIT.EDU'
    username = (os.getenv('LOGNAME') or
                os.getenv('USERNAME') or
                pwd.getpwuid(os.getuid())[0])

    return '{}@{}'.format(username, default_realm)

def take_unprefix(class_):
    res = 0
    while class_.startswith('un'):
        res += 1
        class_ = class_[2:]
    return res, class_
