# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Predicate expression parsing.
'''

from itertools import chain
import inspect
from six.node import (node_predicate, name_imatches, in_place, outgoing,
                      is_link, to_node)
from six.links import from_node, With, Ex
from six.keyword import keyed_with
from six.org import Organisation, Works_at
from six.util import iempty

__all__ = ['parse_predicate', 'ExprError']

class ExprError(StandardError):
    pass

def parse_predicate(model, tokens):
    r'''Parse the sequence of unicode tokens as a predicate expression.
    '''
    parser = Predicate_Parser(model)
    return parser.parse(tokens)

class Predicate_Parser(object):

    OP_AND = '-and'
    OP_OR = '-or'
    OP_NOT = '-not'
    OP_PAREN_OPEN = '('
    OP_PAREN_CLOSE = ')'

    def __init__(self, model):
        self.model = model

    def parse(self, tokens):
        assert tokens
        pred, remain = self._or(tokens)
        if remain:
            raise ExprError('spurious token %r' % remain[0])
        return pred

    def is_operator(self, token):
        # Horribly inefficient.
        for obj in chain([self], inspect.getmro(type(self))):
            for name, value in obj.__dict__.iteritems():
                if name.startswith('OP_') and token == value:
                    return True
        return False

    def _or(self, tokens):
        pred, tokens = self._and(tokens)
        while len(tokens) > 1 and tokens[0] == self.OP_OR:
            pred1, tokens = self._and(tokens[1:])
            pred = pred | pred1
        return pred, tokens

    def _and(self, tokens):
        pred, tokens = self._unary(tokens)
        while tokens:
            if len(tokens) > 1 and tokens[0] == self.OP_AND:
                pred1, tokens = self._unary(tokens[1:])
                pred = pred & pred1
            elif tokens and not self.is_operator(tokens[0]):
                pred1, tokens = self._unary(tokens)
                pred = pred & pred1
            else:
                break
        return pred, tokens

    def _unary(self, tokens):
        if len(tokens) > 1 and tokens[0] == self.OP_NOT:
            pred, tokens = self._unary(tokens[1:])
            return not pred, tokens
        elif len(tokens) > 1 and tokens[0] == self.OP_PAREN_OPEN:
            pred, tokens = self._or(tokens[1:])
            if not (tokens and tokens[0] == self.OP_PAREN_CLOSE):
                raise ExprError('missing "%s"' % self.OP_PAREN_CLOSE)
            return pred, tokens[1:]
        else:
            return self._term(tokens[0]), tokens[1:]

    def _term(self, token):
        if token.startswith('='):
            try:
                kw = self.model.keyword(token[1:])
            except LookupError:
                raise ExprError('no such keyword %r' % kw)
            return keyed_with(kw)
        elif token.startswith('in:'):
            try:
                place = self.model.lookup_place(token[3:])
            except LookupError, e:
                raise ExprError('no such place %r' % token[3:])
            return in_place(place)
        elif (token.startswith('work:') or token.startswith('with:') or
              token.startswith('ex:')):
            i = token.index(':')
            cond = token[:i]
            name = token[i+1:]
            try:
                org = self.model.find(Organisation, name)
            except LookupError:
                raise ExprError('no such organisation %r' % name)
            select = {
                'work': outgoing & is_link(Works_at) & to_node(org),
                'with': outgoing & is_link(With) & to_node(org),
                'ex': outgoing & is_link(Ex) & to_node(org),
            }[cond]
            return node_predicate(lambda node: not iempty(node.links(select)))
        else:
            return name_imatches(token)
