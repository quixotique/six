# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Email address report.
'''

import locale
from six.sort import *
from six.node import *
from six.node import node_predicate
from six.links import *
from six.person import *
from six.family import *
from six.org import *
from six.email import *

def report_email_getopt(parser):
    lang, enc = locale.getlocale()
    parser.set_defaults(encoding=enc, all=False)
    parser.add_option('-a', '--all',
                      action='store_true', dest='all',
                      help='print all possible values')
    parser.add_option('-e', '--encode',
                      action='store', type='string', dest='encoding',
                      help='use ENCODE as output encoding')

def report_email(options, model, predicate, local):
    if predicate is None:
        predicate = node_predicate(lambda node: True)
        options.all = False
    itemiser = Itemiser()
    itemiser.update(model.nodes(is_other(instance_p(NamedNode) & predicate)))
    # Remove entries for families for which one or more of the heads was found.
    for person in filter(lambda node: isinstance(node, Person), itemiser):
        for belongs_to in person.links(outgoing & is_link(Belongs_to)):
            if belongs_to.is_head:
                itemiser.discard(belongs_to.family)
    for item in sorted(itemiser.items()):
        if item is not item.single:
            continue
        node = item.node
        print_emails(node, options.encoding)
        stop = lambda node: False
        if isinstance(node, Organisation):
            pred = ((incoming & is_link(Works_at)) |
                    (outgoing & is_link(Belongs_to)) |
                    (outgoing & is_link(Resides_at)))
            if not options.all:
                stop = instance_p(Person)
        elif isinstance(node, Family):
            pred = ((outgoing & is_link(Works_at)) |
                    (incoming & is_link(Belongs_to)) |
                    (outgoing & is_link(Resides_at)))
            if not options.all:
                stop = instance_p(Organisation)
        elif isinstance(node, Person):
            pred = ((outgoing & is_link(Belongs_to)) |
                    (outgoing & is_link(Resides_at)) |
                    (outgoing & is_link(Works_at)))
            if not options.all:
                stop = instance_p(Organisation)
        for tup in sorted(node.find_nodes(pred, stop=stop), key=len):
            print_emails(tup[-1], options.encoding)

def print_emails(node, encoding):
    namenode = node
    if isinstance(node, Link):
        if hasattr(node, 'person'):
            namenode = node.person
        elif hasattr(node, 'who'):
            namenode = node.who
        elif hasattr(node, 'org'):
            namenode = node.org
    if isinstance(namenode, Person):
        name = namenode.email_address_name()
    else:
        name = unicode(namenode)
    printed = 0
    for addr in node.nodes(outgoing & is_link(Has_email)):
        print addr.format(name, encoding)
        printed += 1
    return printed
