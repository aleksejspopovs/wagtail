import shlex

import curses
import curses.panel

from args import StandaloneArgParser, ArgParserException
from filtering import NopFilterSingleton, Filter
from ui.utils import curse_string

def parse_cmdline_into_events(cmdline):
    result = []

    try:
        command, *args = shlex.split(cmdline) or ['']
    except ValueError as error:
        return [('status', 'Parsing error: {}'.format(error.args))]

    if command == '':
        pass
    elif command == 'zwrite':
        parser = StandaloneArgParser()
        parser.add_argument('-c', '--class', default='MESSAGE',
            dest='class_')
        parser.add_argument('-i', '--instance', default='PERSONAL')
        parser.add_argument('-O', '--opcode', default='')
        parser.add_argument('-d', '--deauth', action='store_true')
        parser.add_argument('-S', '--sender', default=None)
        parser.add_argument('-s', '--signature', default=None)
        parser.add_argument('recipients', nargs='*')

        try:
            opts = parser.parse_args(args)
        except ArgParserException as error:
            result.append(('status', error.args[0]))
        else:
            result.append(('zwrite', opts))
    elif (command == 'sub') or (command == 'unsub'):
        if len(args) == 0:
            result.append(('status',
                '[un]sub needs 1-3 args: class [instance [recipient]]'))
        else:
            class_ = args[0]
            instance = args[1] if len(args) >= 2 else '*'
            recipient = args[2] if len(args) == 3 else '*'

            if command == 'sub':
                result.append(('subscribe', class_, instance, recipient))
            else:
                result.append(('unsubscribe', class_, instance, recipient))
    elif command == 'import_zsubs':
        if len(args) > 1:
            result.append('status',
                'import_zsubs takes just one optional argument, a path.')
        else:
            result.append(('import_zsubs', args[0] if len(args) > 0 else None))
    elif command == 'reload_config':
        if len(args) == 0:
            result.append(('reload_config', ))
        else:
            result.append(('status', 'reload_config doesn\'t take arguments.'))
    elif command == 'filter':
        if len(args) == 0:
            result.append(('filter', NopFilterSingleton))
        elif len(args) == 1:
            # TODO: try to eliminate need for quotes around filter
            try:
                new_filter = Filter(args[0])
            except SyntaxError as error:
                result.append(('status',
                    'Syntax error: {}'.format(error.args[0])))
            else:
                result.append(('filter', Filter(args[0])))
        else:
            result.append(('status', 'Too many arguments for filter.'))
    elif command == 'quit':
        if len(args) == 0:
            result.append(('quit', ))
        else:
            result.append(('status', 'quit doesn\'t take arguments.'))
    else:
        result.append(('status', 'Unknown command {}'.format(command)))

    return result


class CommandLine:
    def __init__(self, screen, initial_input=''):
        self.screen = screen
        # the position & size really doesn't matter
        # because of the call to update_size() below
        self.window = curses.newwin(1, 1, 0, 0)
        self.cols = 1
        self.panel = curses.panel.new_panel(self.window)

        self.input = list(initial_input)
        self.cursor = len(self.input)
        self.first_displayed_character = 0

        # turn the cursor on
        curses.curs_set(1)

        self.update_size()

    def redraw(self):
        self.window.erase()

        self.window.addstr(0, 0, curse_string('> '))

        available_cols = self.cols - 2 - 1
        if self.first_displayed_character + available_cols <= self.cursor:
            self.first_displayed_character = self.cursor - available_cols + 1

        if self.cursor < self.first_displayed_character:
            self.first_displayed_character = self.cursor

        self.window.addnstr(0, 2,
            curse_string(''.join(self.input[self.first_displayed_character:])),
            available_cols)

        self.window.move(0, 2 + self.cursor - self.first_displayed_character)

        self.window.noutrefresh()

    def update_size(self):
        screen_lines, self.cols = self.screen.getmaxyx()
        self.window.resize(1, self.cols)
        self.panel.move(screen_lines - 2, 0)
        curses.panel.update_panels()

        self.redraw()

    def handle_keypress(self, key):
        result = []

        if key == curses.KEY_BACKSPACE:
            if self.cursor != 0:
                del self.input[self.cursor - 1]
                self.cursor -= 1
        elif key == curses.KEY_DC: # Delete Character
            if self.cursor < len(self.input):
                del self.input[self.cursor]
        elif key == curses.KEY_LEFT:
            if self.cursor != 0:
                self.cursor -= 1
        elif key == curses.KEY_RIGHT:
            if self.cursor != len(self.input):
                self.cursor += 1
        elif isinstance(key, str) and key.isprintable():
            self.input.insert(self.cursor, key)
            self.cursor += 1
        elif key == '\n':
            result.append(('cmdline_close', ))
            result.extend(parse_cmdline_into_events(''.join(self.input)))
        elif key == '\x03': # Ctrl+C
            result.append(('cmdline_close', ))

        self.redraw()

        return result

    def close(self):
        self.panel.hide()
        curses.panel.update_panels()
        del self.panel

        curses.curs_set(0)
