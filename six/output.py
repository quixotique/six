# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Formatted output.
'''

from six.struct import struct

__all__ = ['Treebuf']

class Treebuf(object):

    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self.__dict__.update(kwargs)
        self._lines = []
        self._line = []
        self._level = 0
        self._tl = self

    def nl(self):
        self._tl._lines.append(struct(level=self._level,
                                      text=u''.join(self._line)))
        self._line = []

    def add(self, *text, **kwargs):
        if kwargs:
            text = map(decorate(**kwargs), text)
        self._line.extend(text)

    def sub(self):
        return _Sub_Treebuf(self)

    def as_text(self, indent=3):
        r = []
        for line in self._tl._lines:
            if line.level >= self._level:
                r.append(' ' * indent * (line.level - self._level))
                r.append(line.text)
                r.append('\n')
        return u''.join(r)

    def __unicode__(self):
        return self.as_text()

class _Sub_Treebuf(Treebuf):

    def __init__(self, tl):
        self.__dict__.update(tl._tl._kwargs)
        self._tl = tl._tl
        self._level = tl._level + 1
        self._line = []

def decorate(bold=False, underline=False):
    def _iter(text):
        for c in text:
            if underline:
                yield '_\x08'
            yield c
            if bold:
                yield '\x08'
                yield c
    return lambda text: ''.join(_iter(text))
