import sqlite3

from zpipe.python.zpipe import Zephyrgram

class Database:
    def __init__(self):
        self.db = sqlite3.connect('/tmp/messages.sqlite3')

        self.initialize_schema()
        # self.populate_with_test_data()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        with self.db:
            self.db.execute('PRAGMA optimize')
        self.db.close()

    def initialize_schema(self):
        version_table = self.db.execute('''
            SELECT *
            FROM sqlite_master
            WHERE type = 'table'
            AND name = 'version' ''').fetchone()

        if version_table is None:
            # database does not exist
            with self.db:
                self.db.execute('''
                    CREATE TABLE version
                    (version INTEGER)''')
                self.db.execute('''
                    INSERT INTO version
                    VALUES (1)''')
                self.db.execute('''
                    CREATE TABLE messages
                    (id INTEGER PRIMARY KEY,
                     sender TEXT,
                     class TEXT NOT NULL,
                     instance TEXT NOT NULL,
                     recipient TEXT,
                     opcode TEXT NOT NULL,
                     auth INTEGER,
                     fields BLOB,
                     time INT)''')
        else:
            # database exists, must check version and migrate if necessary
            version = self.db.execute('SELECT version FROM version').fetchone()
            version = version[0]

            assert version == 1

    def populate_with_test_data(self):
        with self.db:
            for i in range(100):
                self.db.execute('''
                    INSERT INTO messages
                    VALUES (NULL, 'aleksejs@ATHENA.MIT.EDU',
                            'aleksejs', 'hello', NULL, '', 1,
                            ?, 0)''', b'zsig!\x00hello {}'.format(i))

    def get_message(self, index):
        cursor = self.db.execute('SELECT * FROM messages WHERE id=?', (index, ))
        result = cursor.fetchone()

        if result is None:
            return None

        return self._tuple_to_zephyrgram(result)

    def append_message(self, msg):
        with self.db:
            self.db.execute('''
                INSERT INTO messages
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                self._zephygram_to_tuple(msg))

    def _tuple_to_zephyrgram(self, data):
        _, sender, class_, instance, recipient, opcode, auth, fields, time = \
            data
        auth = bool(auth)
        fields = [x.decode() for x in fields.split(b'\x00')]
        return Zephyrgram(sender, class_, instance, recipient, opcode,
            auth, fields, time)

    def _zephygram_to_tuple(self, msg):
        fields = b'\x00'.join(x.encode() for x in msg.fields)
        return (None, msg.sender, msg.cls, msg.instance, msg.recipient,
            msg.opcode, msg.auth, fields, msg.time)

    def first_index(self):
        # returns None on empty database
        return self.db.execute('SELECT min(id) FROM messages').fetchone()[0]

    def last_index(self):
        # returns None on empty database
        return self.db.execute('SELECT max(id) FROM messages').fetchone()[0]

    def advance(self, index, delta):
        if delta == 0:
            return index
        elif delta < 0:
            result = self.db.execute('''
                SELECT id FROM messages
                WHERE id < ?
                ORDER BY id DESC
                LIMIT 1 OFFSET ?''', (index, abs(delta) - 1)).fetchone()

            if result is None:
                return self.first_index()
            return result[0]
        elif delta > 0:
            result = self.db.execute('''
                SELECT id FROM messages
                WHERE id > ?
                ORDER BY id ASC
                LIMIT 1 OFFSET ?''', (index, delta - 1)).fetchone()

            if result is None:
                return self.last_index()
            return result[0]

    def get_messages_starting_with(self, index, count):
        cursor = self.db.execute('''
            SELECT * FROM messages
            WHERE id >= ?
            ORDER BY id ASC
            LIMIT ?''', (index, count))

        row = cursor.fetchone()
        while row is not None:
            yield (row[0], self._tuple_to_zephyrgram(row))
            row = cursor.fetchone()
