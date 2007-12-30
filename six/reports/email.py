# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Booklet report.
'''

from six.sort import *
from six.node import *
from six.links import *
from six.person import *
from six.family import *
from six.org import *
from six.email import *

def report_email(options, model, predicate, local, encoding):
    if predicate is None:
        predicate = from_node(Person) | from_node(Company) | from_node(Family)
        options.all = False
    itemiser = Itemiser()
    itemiser.update(model.nodes(predicate))
    # Remove entries for families for which one or more of the heads was found.
    for person in filter(lambda node: isinstance(node, Person), itemiser):
        for belongs_to in person.links(outgoing & is_link(Belongs_to)):
            if belongs_to.is_head:
                itemiser.discard(belongs_to.family)
    for item in sorted(itemiser.items()):
        if item is not item.single:
            continue
        node = item.node
        print_emails(node, encoding)
        stop = lambda node: False
        if isinstance(node, Organisation):
            pred = ((incoming & is_link(Works_at)) |
                    (outgoing & is_link(Belongs_to)) |
                    (outgoing & is_link(Resides_at)))
            if not options.all:
                stop = lambda node: isinstance(node, Person)
        elif isinstance(node, Family):
            pred = ((outgoing & is_link(Works_at)) |
                    (incoming & is_link(Belongs_to)) |
                    (outgoing & is_link(Resides_at)))
            if not options.all:
                stop = lambda node: isinstance(node, Organisation)
        else:
            assert isinstance(node, Person)
            pred = ((outgoing & is_link(Belongs_to)) |
                    (outgoing & is_link(Resides_at)) |
                    (outgoing & is_link(Works_at)))
            if not options.all:
                stop = lambda node: isinstance(node, Organisation)
        for tup in sorted(node.find_nodes(pred, stop=stop), key=len):
            print_emails(tup[-1], encoding)

def print_emails(node, encoding):
    name = None
    if isinstance(node, NamedNode):
        name = unicode(node)
    elif isinstance(node, Link):
        if hasattr(node, 'person'):
            name = unicode(node.person)
        elif hasattr(node, 'who'):
            name = unicode(node.who)
        elif hasattr(node, 'org'):
            name = unicode(node.org)
    printed = 0
    for addr in node.nodes(outgoing & is_link(Has_email)):
        print addr.format(name, encoding)
        printed += 1
    return printed
