import curses
import curses.panel

from ui.utils import curse_string

class CommandLine:
    def __init__(self, screen):
        self.screen = screen
        # the position & size really doesn't matter
        # because of the call to update_size() below
        self.window = curses.newwin(1, 1, 0, 0)
        self.cols = 1
        self.panel = curses.panel.new_panel(self.window)

        self.input = []
        self.cursor = 0

        self.update_size()

    def redraw(self):
        self.window.erase()

        self.window.addstr(0, 0, curse_string('> '))

        # TODO: handle commands that don't fit on the screen
        self.window.addstr(0, 2, curse_string(''.join(self.input)))
        self.window.chgat(0, 2 + self.cursor, 1, curses.A_REVERSE)

        self.window.noutrefresh()

    def update_size(self):
        screen_lines, self.cols = self.screen.getmaxyx()
        self.window.resize(1, self.cols)
        self.panel.move(screen_lines - 2, 0)
        curses.panel.update_panels()

        self.redraw()

    def handle_keypress(self, key):
        result = (None, )

        if key == '\n':
            result = ('cmdline_close', ''.join(self.input))
        elif key == curses.KEY_BACKSPACE:
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

        self.redraw()

        return result

    def close(self):
        self.panel.hide()
        curses.panel.update_panels()
        del self.panel
