import ast
import sqlite3

# unfortunately, the only way to quote a literal using the Python SQLite
# bindings is to do a "SELECT quote(?)" query.
_sqlite_tmp = sqlite3.connect(':memory:')

def sqlite_quote(s, lower=False):
    if lower:
        return _sqlite_tmp.execute('SELECT quote(lower(?))', (s, )).fetchone()[0]
    else:
        return _sqlite_tmp.execute('SELECT quote(?)', (s, )).fetchone()[0]

class Filter:
    def to_sql(self):
        assert False, 'abstract'

    def name(self):
        assert False, 'abstract'

class ParsedFilter(Filter):
    def __init__(self, code):
        self.code = code
        self.tree = ast.parse(code, mode='eval')

        self.sql = self._to_sql(self.tree)

    def _to_sql(self, root):
        if isinstance(root, ast.Expression):
            return self._to_sql(root.body)
        elif isinstance(root, ast.Num):
            return str(root.n)
        elif isinstance(root, ast.Str):
            return sqlite_quote(root.s)
        elif isinstance(root, ast.Name):
            # because we're parsing with mode='eval', we can't be assigning
            # a value to a variable or deleting it
            assert isinstance(root.ctx, ast.Load)

            field_map = {
                'class_': 'class',
                'cla': 'class',
                'instance': 'instance',
                'ins': 'instance',
                'recipient': 'recipient',
                'rec': 'recipient',
                'sender': 'sender',
                'sen': 'sender',
                'opcode': 'opcode',
                'opc': 'opcode',
                'signature': 'signature',
                'sig': 'signature',
                'body': 'body',
                'bod': 'body'
            }

            if root.id not in field_map:
                raise SyntaxError('unknown field {}'.format(root.id))

            return field_map[root.id]
        elif isinstance(root, ast.UnaryOp):
            if not isinstance(root.op, ast.Not):
                raise SyntaxError('invalid unary operator')

            return 'NOT ({})'.format(self._to_sql(root.operand))
        elif isinstance(root, ast.BoolOp):
            assert isinstance(root.op, ast.Or) or isinstance(root.op, ast.And)
            op = ' AND ' if isinstance(root.op, ast.And) else ' OR '
            return op.join('({})'.format(self._to_sql(x)) for x in root.values)
        elif isinstance(root, ast.Compare):
            if len(root.ops) != 1:
                raise SyntaxError('multiple comparisons are not supported')

            op = ''
            # we need special handling for GLOB and NOT GLOB to make them
            # case-insensitive
            lower = False
            if isinstance(root.ops[0], ast.Eq):
                op = '='
            elif isinstance(root.ops[0], ast.NotEq):
                op = '!='
            elif isinstance(root.ops[0], ast.Lt):
                op = '<'
            elif isinstance(root.ops[0], ast.LtE):
                op = '<='
            elif isinstance(root.ops[0], ast.Gt):
                op = '>'
            elif isinstance(root.ops[0], ast.GtE):
                op = '>='
            elif isinstance(root.ops[0], ast.Is):
                op = 'GLOB'
                lower = True
            elif isinstance(root.ops[0], ast.IsNot):
                op = 'NOT GLOB'
                lower = True
            else:
                raise SyntaxError('unknown comparison operation')

            if lower:
                return 'lower({}) {} lower({})'.format(self._to_sql(root.left),
                    op, self._to_sql(root.comparators[0]))
            else:
                return '({}) {} ({})'.format(self._to_sql(root.left), op,
                    self._to_sql(root.comparators[0]))
        else:
            raise SyntaxError('unknown syntax tree node {}'
                .format(ast.dump(root)))

    def to_sql(self):
        return self.sql

    def name(self):
        return self.code

class NopFilter(Filter):
    def to_sql(self):
        return '1'

    def name(self):
        return None

class RelatedFilter(Filter):
    def __init__(self, app, message, class_only=False):
        if message.is_personal():
            other_person = message.sender
            if (other_person == app.principal) or (other_person is None):
                other_person = message.recipient

            self._name = 'personals with {}'.format(other_person)
            other_sql = sqlite_quote(other_person, lower=True)
            self.sql = ('(lower(class) GLOB "message") AND '
                        '((lower(sender) GLOB {}) OR (lower(recipient) GLOB {}))'
                       ).format(other_sql, other_sql)
        else:
            if class_only:
                self._name = 'class {}'.format(message.class_)
                class_sql = sqlite_quote('*' + message.class_, lower=True)
                self.sql = 'lower(class) GLOB {}'.format(class_sql)
            else:
                self._name = 'instance {}/{}'.format(message.class_, message.instance)
                class_sql = sqlite_quote('*' + message.class_, lower=True)
                instance_sql = sqlite_quote('*' + message.instance + '*')
                self.sql = ('(lower(class) GLOB {}) AND (lower(instance) GLOB {})'
                           ).format(class_sql, instance_sql)

    def to_sql(self):
        return self.sql

    def name(self):
        return self._name

class NegationFilter(Filter):
    def __init__(self, other):
        self._name = 'NOT ({})'.format(other.name())
        self.sql = 'NOT ({})'.format(other.to_sql())

    def to_sql(self):
        return self.sql

    def name(self):
        return self._name


NopFilterSingleton = NopFilter()
