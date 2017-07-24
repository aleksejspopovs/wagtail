import argparse

class ArgParserException(Exception):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

class StandaloneArgParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        kwargs['add_help'] = False
        super().__init__(*args, **kwargs)

    def error(self, message):
        raise ArgParserException(message)
