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

        self.window.bkgd(' ', curses.A_REVERSE)

        self.update_size()

    def redraw(self):
        self.window.erase()

        # not sure why the -1 is required in coordinates
        version = 'wagtail'
        self.window.addstr(0, self.cols - len(version) - 1,
            curse_string(version))

        self.window.noutrefresh()

    def update_size(self):
        screen_lines, self.cols = self.screen.getmaxyx()
        self.window.resize(1, self.cols)
        self.panel.move(screen_lines - 1, 0)
        curses.panel.update_panels()

        self.redraw()

    def handle_keypress(self, key):
        return (None, )
