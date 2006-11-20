# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Data model - contextual data.
'''

from six.world import World
from six.input import InputError
from six.node import *
from six.links import *

__all__ = ['Data', 'Has_context',
           'Data_factory_place', 'Data_factory_nocontext',
           'Data_factory_context',
          ]

class Data(Node):

    r'''An atom of contextual data consists of an ASCII ID string, and a value
    string.  These, combined with the 'context' node to which the data is
    linked, uniquely identifies the atom.'''

    def __init__(self, context, id, value, timestamp=None):
        assert isinstance(id, str)
        assert isinstance(value, basestring)
        super(Data, self).__init__()
        self.id = id
        self.value = value
        Has_context(self, context, timestamp=timestamp)

    def context(self):
        return self.nodes(outgoing & is_link(Has_context)).next()

    def key(self):
        return self.context(), self.id

    def __unicode__(self):
        return u' = '.join((self.id, self.value))

class Has_context(Link):

    r'''Connect a Data node to its context node.  Exactly one of these per Data
    node.
    '''

    def __init__(self, data, context, timestamp=None):
        from six.links import Is_in
        from six.person import Person
        from six.family import Family
        from six.org import Organisation
        assert isinstance(data, Data)
        assert isinstance(context, (Association, Is_in, Person, Family, Organisation))
        super(Has_context, self).__init__(data, context, timestamp=timestamp)
        self.data = data
        self.context = context

class Data_factory_place(object):

    r'''A Data factory that makes data nodes with a context of a given place.
    '''

    def __init__(self, place):
        self._place = place

    def __call__(self, part, who, id, value):
        from six.links import Is_in
        if isinstance(who, Link):
            raise InputError('place-contextual data in a non-place context',
                             line=value)
        if (hasattr(part, 'place') and part.place is not None and
            part.place != self._place):
            raise InputError('invalid data place %s - should be %s' %
                             (part.place, self._place), line=value)
        context = who.link(outgoing & is_link(Is_in) & has_place(self._place))
        if not context:
            context = Is_in(who, self._place)
        return Data(context, id, value, timestamp=part.updated)

class Data_factory_nocontext(object):

    r'''A Data factory that makes data nodes with no context.
    '''

    def __call__(self, part, who, id, value):
        if isinstance(who, Link):
            raise InputError('non-contextual data in a context',
                             line=value)
        if hasattr(part, 'place') and part.place is not None:
            raise InputError('non-contextual data in a place context',
                             line=value)
        return Data(who, id, value, timestamp=part.updated)

class Data_factory_context(object):

    r'''The default Data factory that makes data nodes with whatever context it
    is told to use.
    '''

    def __call__(self, part, context, id, value):
        from six.links import Is_in
        if not isinstance(context, Link):
            place = part.place or context.only_place()
            if not place:
                raise InputError('data context (place) unknown',
                                 line=value)
            context = context.link(outgoing & is_link(Is_in) & has_place(place))
            if not context:
                context = Is_in(context, place)
        return Data(context, id, value, timestamp=part.updated)
