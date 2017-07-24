import curses
import curses.panel

from ui.utils import curse_string

class StatusBar:
    def __init__(self, screen):
        self.screen = screen
        # the position & size really doesn't matter
        # because of the call to update_size() below
        self.window = curses.newwin(1, 1, 0, 0)
        self.cols = 1
        self.panel = curses.panel.new_panel(self.window)

        self.status = ''

        self.window.bkgd(' ', curses.A_REVERSE)

        self.update_size()

    def redraw(self):
        self.window.erase()

        version = 'wagtail'

        available_cols = self.cols - len(version) - 1
        self.window.addstr(0, 0, self.status[:available_cols])

        try:
            self.window.addstr(0, self.cols - len(version),
                curse_string(version))
        except curses.error:
            # addstr will raise an exception when the string touches
            # the lower right corner of a window
            pass

        self.window.chgat(0, self.cols - len(version),
            len(version), curses.A_BOLD | curses.A_REVERSE)

        self.window.noutrefresh()

    def set_status(self, status):
        self.status = status
        self.redraw()

    def clear_status(self):
        self.status = ''
        self.redraw()

    def update_size(self):
        screen_lines, self.cols = self.screen.getmaxyx()
        self.window.resize(1, self.cols)
        self.panel.move(screen_lines - 1, 0)

        curses.panel.update_panels()

        self.redraw()

    def handle_keypress(self, key):
        return []
