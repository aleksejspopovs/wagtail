import sqlite3

from zpipe.python.zpipe import Zephyrgram

from filtering import NopFilterSingleton
from util import take_unprefix

class Database:
    def __init__(self):
        self.db = sqlite3.connect('/tmp/messages.sqlite3')

        self.initialize_schema()
        # self.populate_with_test_data()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()

    def close(self):
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
                self.db.execute('''
                    CREATE TABLE subscriptions
                    (class TEXT NOT NULL,
                     instance TEXT NOT NULL,
                     recipient TEXT NOT NULL,
                     undepth INTEGER NOT NULL,
                     PRIMARY KEY (class, instance, recipient))''')
        else:
            # database exists, must check version and migrate if necessary
            version = self.db.execute('SELECT version FROM version').fetchone()
            version = version[0]

            assert version == 1

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

    def first_index(self, filter=NopFilterSingleton):
        # returns None on empty database
        return self.db.execute('SELECT min(id) FROM messages WHERE {}'
            .format(filter.to_sql())).fetchone()[0]

    def last_index(self, filter=NopFilterSingleton):
        # returns None on empty database
        return self.db.execute('SELECT max(id) FROM messages WHERE {}'
            .format(filter.to_sql())).fetchone()[0]

    def advance(self, index, delta, filter=NopFilterSingleton):
        if delta == 0:
            return index
        elif delta < 0:
            result = self.db.execute('''
                SELECT id FROM messages
                WHERE id < ?
                AND {}
                ORDER BY id DESC
                LIMIT 1 OFFSET ?'''.format(filter.to_sql()),
                (index, abs(delta) - 1)).fetchone()

            if result is None:
                return index
            return result[0]
        elif delta > 0:
            result = self.db.execute('''
                SELECT id FROM messages
                WHERE id > ?
                AND {}
                ORDER BY id ASC
                LIMIT 1 OFFSET ?'''.format(filter.to_sql()),
                (index, delta - 1)).fetchone()

            if result is None:
                return index
            return result[0]

    def get_messages_starting_with(self, index, filter=NopFilterSingleton):
        cursor = self.db.execute('''
            SELECT * FROM messages
            WHERE id >= ?
            AND {}
            ORDER BY id ASC'''.format(filter.to_sql()), (index, ))

        row = cursor.fetchone()
        while row is not None:
            yield (row[0], self._tuple_to_zephyrgram(row))
            row = cursor.fetchone()

    def count_messages_after(self, index, filter=NopFilterSingleton):
        result, = self.db.execute('''
            SELECT count(*) FROM messages
            WHERE id > ?
            AND {}'''.format(filter.to_sql()), (index, )).fetchone()
        return result

    def get_subscriptions(self, expand_un=True):
        cursor = self.db.execute('SELECT * FROM subscriptions')

        row = cursor.fetchone()
        while row is not None:
            class_, instance, recipient, undepth = row
            yield row
            if expand_un:
                for i in range(1, undepth + 1):
                    yield (('un'*i) + class_, instance, recipient, 0)

            row = cursor.fetchone()

    def subscribe(self, class_, instance, recipient):
        undepth, class_stripped = take_unprefix(class_)

        result = self.db.execute('''
            SELECT undepth, rowid
            FROM subscriptions
            WHERE (class = ?)
            AND (instance = ?)
            AND (recipient = ?)''',
            (class_stripped, instance, recipient)).fetchone()

        if result is None:
            with self.db:
                self.db.execute('''
                    INSERT INTO subscriptions
                    VALUES (?, ?, ?, ?)''',
                    (class_stripped, instance, recipient, undepth))
            return [('un'*i + class_stripped, instance, recipient)
                    for i in range(undepth + 1)]
        else:
            existing_undepth, rowid = result
            if existing_undepth < undepth:
                with self.db:
                    self.db.execute('''
                        UPDATE subscriptions
                        SET undepth = ?
                        WHERE rowid = ?''', (undepth, rowid))
                return [('un'*i + class_stripped, instance, recipient)
                        for i in range(existing_undepth + 1, undepth + 1)]
            else:
                return []

    def unsubscribe(self, class_, instance, recipient):
        undepth, _ = take_unprefix(class_)
        if undepth != 0:
            # cannot unsubscribe from an unclass directly
            # TODO: clear error message
            return []

        result = self.db.execute('''
            SELECT undepth, rowid
            FROM subscriptions
            WHERE (class = ?)
            AND (instance = ?)
            AND (recipient = ?)''',
            (class_, instance, recipient)).fetchone()

        if result is None:
            return []

        existing_undepth, rowid = result

        with self.db:
            self.db.execute('''
                DELETE FROM subscriptions
                WHERE rowid = ?''', (rowid, ))

        return [('un'*i + class_, instance, recipient)
                for i in range(existing_undepth + 1)]

    def update_undepth(self, class_, candidate_undepth):
        # no need to run SQL queries if it's obvious nothing will change
        if candidate_undepth == 0:
            return []

        affected = self.db.execute('''
            SELECT instance, recipient
            FROM subscriptions
            WHERE (class = ?)
            AND (undepth < ?)''', (class_, candidate_undepth)).fetchall()

        if len(affected) == 0:
            return []

        with self.db:
            self.db.execute('''
                UPDATE subscriptions
                SET undepth = max(undepth, ?)
                WHERE class = ?''', (candidate_undepth, class_))

        return affected
