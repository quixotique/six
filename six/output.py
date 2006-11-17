# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Formatted output.
'''

import textwrap
from six.struct import struct

__all__ = ['Treebuf']

class _Treebuf(object):

    def __init__(self, **kwargs):
        self._kwargs = kwargs
        self.__dict__.update(kwargs)
        self._render = []
        self._level = 0
        self._tl = self

    def nl(self):
        self._tl._render.append(lambda r: r.nl())

    def add(self, *text, **kwargs):
        self._tl._render.append(lambda r: r.set_level(self._level))
        self._tl._render.append(lambda r: r.add(*text, **kwargs))

    def set_wrapmargin(self):
        self._tl._render.append(lambda r: r.set_wrapmargin())

    def wrap(self, *text, **kwargs):
        self._tl._render.append(lambda r: r.set_level(self._level))
        self._tl._render.append(lambda r: r.wrap(*text, **kwargs))

    def sub(self):
        return _Sub_Treebuf(self)

class Treebuf(_Treebuf):

    r'''A treebuf accumulates tree-structured text to be rendered later.
    '''

    def as_text(self, indent=3, width=80):
        r = Tree_Text_Renderer(indent=indent, width=width)
        for func in self._render:
            func(r)
        return r.render()

    def __unicode__(self):
        return self.as_text()

class _Sub_Treebuf(Treebuf):

    def __init__(self, tl):
        self.__dict__.update(tl._tl._kwargs)
        self._tl = tl._tl
        self._level = tl._level + 1

class Tree_Text_Renderer(object):

    def __init__(self, width=80, indent=3):
        self.width = width
        self.indent = indent
        self._output = []
        self._level = 0
        self._wrapmargin = 0

    def set_level(self, level):
        self._level = level
        self._margin = self.indent * level

    def _add(self, piece, decorator=None):
        if self._column == 0:
            self._column = self._margin
            self._output.append(' ' * self._column)
        self._column += len(piece)
        if decorator:
            piece = decorator(piece)
        self._output.append(piece)

    def add(self, *text, **kwargs):
        decorator = self.decorator(**kwargs) if kwargs else lambda x: x
        for piece in text:
            self._add(piece, decorator)

    def nl(self):
        self._output.append('\n')
        self._column = 0

    def set_wrapmargin(self):
        self._wrapmargin = self._column or self._margin

    def wrap(self, *text, **kwargs):
        decorator = self.decorator(**kwargs) if kwargs else lambda x: x
        wrapper = textwrap.TextWrapper(width=self.width,
                                       initial_indent=' '*self._column,
                                       subsequent_indent=' '*self._wrapmargin)
        wrapped = wrapper.wrap(''.join(text))
        self._add(wrapped[0][self._column:], decorator)
        for line in wrapped[1:]:
            self.nl()
            self._add(line[self._margin:], decorator)

    def render(self):
        return u''.join(self._output)

    @classmethod
    def decorator(class_, bold=False, underline=False):
        def _iter(text):
            for c in text:
                if underline:
                    yield '_\x08'
                yield c
                if bold:
                    yield '\x08'
                    yield c
        return lambda text: ''.join(_iter(text))
