import importlib
import importlib.util
import os
import os.path
import shutil
import sys

EXPECTED_CONFIG_VERSION = 1

class ConfigManager:
    def __init__(self):
        if os.getenv('XDG_CONFIG_HOME') is not None:
            self.path = os.path.join(os.getenv('XDG_CONFIG_HOME'), 'wagtail',
                'config.py')
        else:
            self.path = os.path.expanduser('~/.config/wagtail/config.py')

        os.makedirs(os.path.dirname(self.path), exist_ok=True)

        if not os.path.exists(self.path):
            shutil.copyfile(
                os.path.join(os.path.dirname(os.path.abspath(__file__)),
                    'example_config.py'),
                self.path)

        self.module_name = 'wagtail_user_config'
        self.spec = importlib.util.spec_from_file_location(self.module_name,
            self.path)
        self.reload()

    def reload(self):
        self.module = importlib.util.module_from_spec(self.spec)
        self.spec.loader.exec_module(self.module)

        self.check_version()

    def check_version(self):
        # TODO: nicer exception
        if self.module.version != EXPECTED_CONFIG_VERSION:
            raise Exception(('Config vesion mismatch. Version {} expected, '
                'version {} found.').format(EXPECTED_CONFIG_VERSION,
                    self.module.version))

    def __getattr__(self, name):
        if hasattr(self.module, name):
            return getattr(self.module, name)
        raise AttributeError

