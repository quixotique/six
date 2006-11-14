# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Comment - miscellaneous text that can be attached to just about any node.
'''

from six.input import InputError
from six.node import *

__all__ = ['Comment', 'Has_comment',
          ]

class Comment(Node):

    r'''A comment is just a piece of text.
    '''

    def __init__(self, text):
        assert isinstance(text, basestring)
        super(Comment, self).__init__()
        self.text = text

    def __unicode__(self):
        return unicode(self.text)

    def __str__(self):
        return str(unicode(self))

    def __repr__(self):
        return '%s(%r)' % (self.__class__.__name__, self.text)

    @classmethod
    def parse(class_, text, world=None, place=None, default_place=None):
        r'''
            >>> Comment.parse(u'This is a comment')
            (Comment(u'This is a comment'), None)

        '''
        return class_(text), None

class Has_comment(Link):

    r'''Connect a Comment to a node.
    '''

    def __init__(self, node, comment, timestamp=None):
        assert isinstance(comment, Comment)
        super(Has_comment, self).__init__(node, comment, timestamp=timestamp)
        self.node = node
        self.comment = comment
