
import re


QUOTING = re.compile(r'^(?:\s*>\s*)+')


class Line:
    def __init__(self):
        self.level = 0
        self.text = ''
        self.original_text = ''

    def __repr__(self):
        return '<%s level=%s text=%r>' % (type(self).__name__, self.level, self.text)


class Block:
    def __init__(self):
        self.level = 0
        self.content = []
        self.header = []

    def __repr__(self):
        return f'<%s level=%s content=%s>' % (type(self).__name__, self.level, self.content)


class Parser:
    def __init__(self):
        self.level = 0
        self.ret = []
        self.buf = []
        self.lines = []

    def _build_lines(self, text):
        for line in text.splitlines():
            q = Line()
            q.original_text = line

            mtc = QUOTING.match(line)
            if mtc:
                q.text = line[mtc.end():]
                q.level = mtc.group().count('>')
            else:
                q.text = q.original_text

            self.lines.append(q)

    def parse(self, text):
        self._build_lines(text)

        for q in self.lines:
            if q.level == self.level:
                self.buf.append(q)
            else:
                self._dump_buf()
                self.level = q.level
                self.buf.append(q)

        if self.buf:
            self._dump_buf()

        return self.ret

    def _dump_buf(self):
        if not self.buf:
            return

        b = Block()
        b.level = self.buf[-1].level
        b.content = self.buf
        self.buf = []

        if not self.level:
            self.ret.append(b)
            return

        if not self.ret:
            self.ret.append(b)
            return

        last = self.ret[-1]

        if not last.level:
            self.ret.append(b)
            return

        self._dump_buf_recurse(b, self.ret)

    def _dump_buf_recurse(self, b, current):
        last = current[-1]

        if last.level == b.level:
            last.content.extend(b.content)
            return
        if last.level > b.level:
            current[-1] = b
            b.content.insert(0, last)
            return

        if isinstance(last, Block):
            self._dump_buf_recurse(b, last.content)
        else:
            current.append(b)


def indent_recursive(block):
    block.level += 1
    if isinstance(block, Block):
        block.level += 1
        for sub in block.content:
            indent_recursive(sub)


def to_text(ls):
    parts = []

    def recurse(block):
        if isinstance(block, Line):
            if block.level:
                parts.append(('>' * block.level) + ' ' + block.text)
            else:
                parts.append(block.text)
        else:
            for sub in block.content:
                recurse(sub)

    for block in ls:
        recurse(block)

    return '\n'.join(parts)


if __name__ == '__main__':
    import pprint
    ret = Parser().parse('''
foo 1

> bar 1
> bar 2
> > baz 1
> > baz 2
> bar 3
> bar 4

foo 2

>>> qqq
>> qq
> q

foo 3

> q
>> qq
>>> qqq

foo 4

> q
>>> qqq
>> qq
> > qq 2
> > > qqq 2

''')
    pprint.pprint(ret)

