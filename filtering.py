import ast
import sqlite3

# unfortunately, the only way to quote a literal using the Python SQLite
# bindings is to do a "SELECT quote(?)" query.
_sqlite_tmp = sqlite3.connect(':memory:')

class Filter:
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
            quoted, = \
                _sqlite_tmp.execute('SELECT quote(?)', (root.s, )).fetchone()
            return quoted
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

class NopFilter(Filter):
    def __init__(self):
        pass

    def to_sql(self):
        return '1'

NopFilterSingleton = NopFilter()
