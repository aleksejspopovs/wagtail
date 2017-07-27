import shlex

import curses
import curses.panel

from ui.utils import curse_string

def take_up_to(it, n):
    res = []
    for i in range(n):
        try:
            element = next(it)
        except StopIteration:
            break
        else:
            res.append(element)
    return res


class MainWindow:
    def __init__(self, screen, db, config):
        self.db = db
        self.config = config
        self.screen = screen
        # the size doesn't matter because of the call to update_size() below
        self.window = curses.newwin(1, 1, 0, 0)
        self.lines = self.cols = 1
        self.panel = curses.panel.new_panel(self.window)

        self.init_colors()

        self.top_index = self.current_index = self.last_visible_message = None
        self.update_size()

    def init_colors(self):
        self.colors = {
            'default': -1,
            'black': curses.COLOR_BLACK,
            'blue': curses.COLOR_BLUE,
            'cyan': curses.COLOR_CYAN,
            'green': curses.COLOR_GREEN,
            'magenta': curses.COLOR_MAGENTA,
            'red': curses.COLOR_RED,
            'white': curses.COLOR_RED,
            'yellow': curses.COLOR_YELLOW
        }

        self.color_pairs = {}
        i = 1
        for fg in self.colors:
            for bg in self.colors:
                curses.init_pair(i, self.colors[fg], self.colors[bg])
                self.color_pairs[fg, bg] = curses.color_pair(i)
                i += 1

    def measure_message_height(self, message):
        return 2 + message.fields[1].rstrip().count('\n')

    def draw_message(self, row, message, is_current):
        properties = self.config.get_zgram_display_properties(message,
            is_current)
        fg = properties.get('fg_color', 'default')
        bg = properties.get('bg_color', 'default')
        color_pair = self.color_pairs[fg, bg]

        try:
            self.window.addnstr(row, 2,
                curse_string(properties.get('header', 'ERROR no header returned')),
                self.cols - 2)
        except curses.error:
            # this might try printing onto the end of the last line of the
            # window, which makes curses sad
            pass

        self.window.chgat(row, 0, -1, color_pair)

        if is_current:
            # we add the vertical line, then explicitly set the color for it
            # (instead of doing chgat on the entire line after printing the
            # line) because, for some reason, if we apply chgat to the pipe,
            # it turns into an 'x'
            self.window.addch(row, 0, curses.ACS_VLINE, color_pair)

        empty_row = row + 1
        for i, line in enumerate(message.fields[1].rstrip().split('\n'), 1):
            if row + i == self.lines:
                break

            try:
                self.window.addnstr(row + i, 4, curse_string(line), self.cols - 4)
            except curses.error:
                # this might try printing onto the end of the last line of the
                # window, which makes curses sad
                pass

            self.window.chgat(row + i, 0, -1, color_pair)
            if is_current:
                self.window.addch(row + i, 0, curses.ACS_VLINE, color_pair)

            empty_row = row + i + 1

        return empty_row

    def redraw(self):
        self.window.erase()

        if self.current_index is None:
            self.current_index = self.db.first_index()

            if self.current_index is None:
                self.window.noutrefresh()
                return

        if (self.top_index is None) or (self.current_index < self.top_index):
            self.top_index = self.current_index

        if (self.last_visible_message is not None) and \
           (self.current_index > self.last_visible_message):
            self.top_index = self.current_index

        # every message takes at least 1 line, so we take $2 * self.lines$
        # messages, which is at least two screens worth of messages
        messages = take_up_to(self.db.get_messages_starting_with(
            self.top_index), 2 * self.lines)

        # we don't want the current message to ever start below the lower half
        # of the screen
        current_start = sum(self.measure_message_height(msg) for
            idx, msg in messages
            if idx < self.current_index)

        while current_start * 2 > self.lines:
            current_start -= self.measure_message_height(messages[0][1])
            messages = messages[1:]
            self.top_index = messages[0][0]

        start_row = 0
        for index, msg in messages:
            next_start_row = self.draw_message(start_row, msg,
                index == self.current_index)

            self.last_visible_message = index

            if next_start_row == self.lines:
                break

            start_row = next_start_row

        self.window.noutrefresh()

    def move_to(self, index):
        self.current_index = index

        self.redraw()

    def advance(self, delta):
        if self.current_index is None:
            self.redraw()
            return

        self.current_index = self.db.advance(self.current_index, delta)

        self.redraw()

    def update_size(self):
        self.lines, self.cols = self.screen.getmaxyx()
        self.lines -= 1 # for status bar

        self.window.resize(self.lines, self.cols)

        curses.panel.update_panels()

        self.redraw()

    def handle_keypress(self, key):
        result = []

        if (key == curses.KEY_DOWN) or (key == 'j'):
            self.advance(+1)
        elif (key == curses.KEY_UP) or (key == 'k'):
            self.advance(-1)
        elif (key == '<') or (key == 'g'):
            self.move_to(self.db.first_index())
        elif (key == '>') or (key == 'G'):
            self.move_to(self.db.last_index())
        elif key == curses.KEY_PPAGE: # Previous Page
            # TODO: this does not actually work well, it just
            # scrolls up by one pretty much all the time
            if self.top_index is not None:
                self.move_to(self.db.advance(self.top_index, -1))
        elif key == curses.KEY_NPAGE: # Next Page
            if self.last_visible_message is not None:
                self.move_to(self.db.advance(self.last_visible_message, +1))
        elif key == ':':
            result.append(('cmdline_open', ))
        elif key == 'z':
            result.append(('cmdline_open', 'zwrite '))
        elif (key == 'r') or (key == 'R'):
            message = self.db.get_message(self.current_index)
            if message is not None:
                event = 'cmdline_exec' if key == 'r' else 'cmdline_open'
                if (message.cls.lower() == 'message'):
                    # it's a personal
                    # TODO: handle CCs
                    result.append((event,
                        'zwrite {}'.format(shlex.quote(message.sender))))
                else:
                    result.append((event,
                        'zwrite -c {} -i {} {}'.format(shlex.quote(message.cls),
                            shlex.quote(message.instance),
                            shlex.quote(message.recipient))))
        elif key == 'q':
            result.append(('quit', ))
        else:
            if isinstance(key, str):
                result.append(('status', 'unknown key c{}'.format(
                    [ord(x) for x in key])))
            else:
                result.append(('status', 'unknown key i{}'.format(key)))

        return result
