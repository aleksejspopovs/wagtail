import locale
locale.setlocale(locale.LC_ALL, '')

def curse_string(s):
    return s.encode(locale.getpreferredencoding())
