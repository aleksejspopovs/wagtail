import curses
import curses.panel

from ui.utils import curse_string

from zpipe.python.zpipe import Zephyrgram

def count_while(f, lst):
    res = 0
    for x in lst:
        if f(x):
            res += 1
        else:
            break
    return res

class ZephyrgramComposer:
    def __init__(self, screen, config, zwrite_opts):
        self.screen = screen
        self.config = config
        # the position & size really doesn't matter
        # because of the call to update_size() below
        self.window = curses.newwin(1, 1, 0, 0)
        self.panel = curses.panel.new_panel(self.window)

        self.editor_lines = 7
        self.editor_cols = 80
        self.wrap_cols = 70

        self.buffer = [[]]
        self.cursor_y = self.cursor_x = 0
        self.top = self.left = 0

        self.zwrite_opts = zwrite_opts

        # turn the cursor on
        curses.curs_set(1)

        self.update_size()

    def redraw(self):
        self.window.erase()

        # print title
        title = '{}/{}/{}'.format(self.zwrite_opts.class_,
            self.zwrite_opts.instance, ','.join(self.zwrite_opts.recipients))
        if len(title) > self.editor_cols:
            title = title[:self.editor_cols - 3] + '...'
        self.window.addstr(0, 1, curse_string(title))

        # curses.textpad.rectangle is broken for rectangles touching the lower
        # right corner
        self.window.vline(1, 0, curses.ACS_VLINE, self.editor_lines)
        self.window.hline(0, 1 + len(title), curses.ACS_HLINE,
            self.editor_cols - len(title))
        self.window.hline(self.editor_lines + 1, 1,
            curses.ACS_HLINE, self.editor_cols)
        self.window.vline(1, self.editor_cols + 1,
            curses.ACS_VLINE, self.editor_lines)
        self.window.addch(0, 0, curses.ACS_ULCORNER)
        self.window.addch(0, self.editor_cols + 1, curses.ACS_URCORNER)
        self.window.addch(self.editor_lines + 1, 0, curses.ACS_LLCORNER)
        try:
            self.window.addch(self.editor_lines + 1, self.editor_cols + 1,
                curses.ACS_LRCORNER)
        except curses.error as e:
            pass

        if self.cursor_y < self.top:
            self.top = self.cursor_y
        if self.top + self.editor_lines <= self.cursor_y:
            self.top = self.cursor_y

        if self.cursor_x > len(self.buffer[self.cursor_y]):
            self.cursor_x = len(self.buffer[self.cursor_y])

        if self.cursor_x < self.left:
            self.left = self.cursor_x
        if self.left + self.editor_cols <= self.cursor_x:
            self.left = self.cursor_x


        for y in range(self.editor_lines):
            if self.top + y >= len(self.buffer):
                break
            self.window.addnstr(1 + y, 1, curse_string(
                ''.join(self.buffer[self.top + y]))[self.left:],
                self.editor_cols)

        self.window.move(
            1 + self.cursor_y - self.top,
            1 + self.cursor_x - self.left)

        self.window.noutrefresh()

    def update_size(self):
        screen_lines, screen_cols = self.screen.getmaxyx()

        self.window.resize(self.editor_lines + 2, self.editor_cols + 2)
        self.panel.move(screen_lines - (self.editor_lines + 2) - 1,
            screen_cols - self.editor_cols - 2)

        curses.panel.update_panels()

        self.redraw()

    def handle_keypress(self, key):
        result = []

        if key == curses.KEY_BACKSPACE:
            if self.cursor_x != 0:
                del self.buffer[self.cursor_y][self.cursor_x - 1]
                self.cursor_x -= 1
            elif self.cursor_y != 0:
                self.cursor_x = len(self.buffer[self.cursor_y - 1])
                self.cursor_y -= 1
                self.buffer[self.cursor_y].extend(self.buffer[self.cursor_y+1])
                del self.buffer[self.cursor_y + 1]
        elif key == curses.KEY_DC: # Delete Character
            if self.cursor_x < len(self.buffer[self.cursor_y]):
                del self.buffer[self.cursor_y][self.cursor_x]
            elif self.cursor_y != len(self.buffer) - 1:
                self.buffer[self.cursor_y].extend(self.buffer[self.cursor_y+1])
                del self.buffer[self.cursor_y + 1]
        elif key == curses.KEY_LEFT:
            if self.cursor_x != 0:
                self.cursor_x -= 1
            elif self.cursor_y != 0:
                self.cursor_y -= 1
                self.cursor_x = len(self.buffer[self.cursor_y])
        elif key == curses.KEY_RIGHT:
            if self.cursor_x != len(self.buffer[self.cursor_y]):
                self.cursor_x += 1
            elif self.cursor_y != len(self.buffer) - 1:
                self.cursor_y += 1
                self.cursor_x = 0
        elif key == curses.KEY_UP:
            if self.cursor_y != 0:
                self.cursor_y -= 1
        elif key == curses.KEY_DOWN:
            if self.cursor_y != len(self.buffer) - 1:
                self.cursor_y += 1
            else:
                self.cursor_x = len(self.buffer[self.cursor_y])
        elif key == '\n':
            if ((self.cursor_y == len(self.buffer) - 1) and
                (self.cursor_x == 1) and
                (self.buffer[self.cursor_y] == ['.'])):

                recipients = self.zwrite_opts.recipients or [None]
                body = '\n'.join(''.join(x) for x in self.buffer[:-1])

                zsig = self.zwrite_opts.signature
                if zsig is None:
                    zsig = self.config.compute_zsig(self.zwrite_opts.sender,
                        self.zwrite_opts.class_,
                        self.zwrite_opts.instance,
                        recipients,
                        self.zwrite_opts.opcode,
                        not self.zwrite_opts.deauth,
                        body)

                result.append(('composer_close', ))
                result.append(('send_zephyrgrams',
                    [Zephyrgram(self.zwrite_opts.sender,
                        self.zwrite_opts.class_,
                        self.zwrite_opts.instance,
                        recipient,
                        self.zwrite_opts.opcode,
                        not self.zwrite_opts.deauth,
                        [zsig, body],
                        None)
                     for recipient in recipients]))

            self.buffer[self.cursor_y], new_line = \
                (self.buffer[self.cursor_y][:self.cursor_x:],
                 self.buffer[self.cursor_y][self.cursor_x:])

            # autoindent
            indent = count_while(lambda x: x == ' ', self.buffer[self.cursor_y])
            new_line = [' '] * indent + new_line

            self.buffer.insert(self.cursor_y + 1, new_line)
            self.cursor_y += 1
            self.cursor_x = indent
        elif isinstance(key, str) and key.isprintable():
            self.buffer[self.cursor_y].insert(self.cursor_x, key)
            self.cursor_x += 1

            # wrapping
            # will only act if cursor is on the end of the line
            if ((self.cursor_x == len(self.buffer[self.cursor_y])) and
                (self.cursor_x == self.wrap_cols + 1) and
                (' ' in self.buffer[self.cursor_y])):
                last_space = (len(self.buffer[self.cursor_y]) -
                    self.buffer[self.cursor_y][::-1].index(' ')) - 1
                self.buffer[self.cursor_y], new_line = \
                    (self.buffer[self.cursor_y][:last_space],
                     self.buffer[self.cursor_y][last_space + 1:])

                # autoindent
                indent = count_while(lambda x: x == ' ',
                    self.buffer[self.cursor_y])
                new_line = [' '] * indent + new_line

                self.buffer.insert(self.cursor_y + 1, new_line)
                self.cursor_y += 1
                self.cursor_x = len(new_line)
        elif key == '\x03': # Ctrl+C
            result.append(('composer_close', ))

        self.redraw()

        return result

    def close(self):
        self.panel.hide()
        curses.panel.update_panels()
        del self.panel

        curses.curs_set(0)
