# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Phone numbers report.
'''

import locale
from sixx.sort import *
from sixx.model import *
from sixx.node import *
from sixx.links import *
from sixx.person import *
from sixx.family import *
from sixx.org import *
from sixx.reports.dump import dump_comments, telephones, qual_home, qual_work

def report_phone_getopt(parser):
    lang, enc = locale.getlocale()
    parser.set_defaults(encoding=enc)
    parser.add_option('-e', '--encode',
                      action='store', type='string', dest='encoding',
                      help='use ENCODE as output encoding')

def report_phone(options, model, predicate, local):
    if predicate is None:
        predicate = is_principal & is_other(instance_p(Person) | instance_p(Company))
    tkw = {'fax': False, 'bold': True}
    itemiser = Itemiser()
    itemiser.update(model.nodes(is_other(instance_p(NamedNode)) & predicate))
    # Remove entries for families for which one or more of the heads was found.
    people = [node for node in itemiser if isinstance(node, Person)]
    for person in people:
        for belongs_to in person.links(outgoing & is_link(Belongs_to)):
            if belongs_to.is_head:
                itemiser.discard(belongs_to.family)
    from sixx.output import Treebuf
    tree = Treebuf(local=local)
    for item in sorted(itemiser.items()):
        if item is not item.single:
            continue
        node = item.node
        tree.nl()
        sub = tree.sub()
        if isinstance(node, Person):
            tree.add(node, underline=True)
            for aka in node.aka:
                tree.add(' (')
                tree.add(aka)
                tree.add(')')
            tree.nl()
            dump_comments(node, sub)
            telephones(node, sub, **tkw)
            for tup in node.find_nodes(
                    (outgoing & is_link(Belongs_to)) |
                    (outgoing & is_link(Resides_at)) |
                    (outgoing & is_link(Works_at))):
                telephones_qual(tup, sub, **tkw)
        elif isinstance(node, Family):
            tree.add(node, underline=True)
            for aka in node.aka:
                tree.add(' (')
                tree.add(aka)
                tree.add(')')
            tree.nl()
            dump_comments(node, sub)
            telephones(node, sub, **tkw)
            for tup in node.find_nodes(outgoing & is_link(Resides_at)):
                comment = []
                for node1 in tup:
                    if isinstance(node1, Resides_at):
                        comment.append(node1.residence.lines[0])
                telephones(tup[-1], sub, comment=', '.join(comment), **tkw)
            for link in node.links(incoming & is_link(Belongs_to)):
                sub.add(link.person.familiar_name(), underline=True)
                sub.nl()
                subsub = sub.sub()
                telephones(link, subsub, **tkw)
                telephones(link.person, subsub, **tkw)
                for tup in link.person.find_nodes(
                        (outgoing & is_link(Works_at)) |
                        (outgoing & is_link(Resides_at))):
                    telephones_qual(tup, subsub, **tkw)
        elif isinstance(node, Organisation):
            tree.add(node, underline=True)
            if isinstance(node, Department):
                link = node.link(incoming & is_link(Has_department))
                if link:
                    tree.add(', ', link.company)
            for aka in node.aka:
                tree.add(' (')
                tree.add(aka)
                tree.add(')')
            tree.nl()
            dump_comments(node, sub)
            telephones(node, sub, **tkw)
            telephones_org(node, sub, **tkw)
            for loc in node.nodes(outgoing & is_link(Located_at)):
                telephones_org(loc, sub, **tkw)
            for dept in node.nodes(outgoing & is_link(Has_department)):
                sub.add(dept, underline=True)
                sub.nl()
                subsub = sub.sub()
                telephones(dept, subsub, **tkw)
                telephones_org(dept, subsub, **tkw)
    print(str(tree))

def telephones_org(org, tree, **tkw):
    for tup in org.find_nodes(outgoing & is_link(Resides_at)):
        comment = []
        for node1 in tup:
            if isinstance(node1, Resides_at):
                comment.append(node1.residence.lines[0])
        telephones(tup[-1], tree, comment=', '.join(comment), **tkw)
    for link in org.links(incoming & is_link(Works_at)):
        tree.add(link.person, underline=True)
        if link.position:
            tree.add(', ', link.position)
        tree.nl()
        sub = tree.sub()
        telephones(link, sub, **tkw)
        telephones(link.person, sub, **tkw)
        for tup in link.person.find_nodes(
                (outgoing & is_link(Belongs_to)) |
                (outgoing & is_link(Resides_at))):
            telephones_qual(tup, sub, **tkw)

def telephones_qual(tup, tree, **kwargs):
    qual = None
    comment = []
    for node in tup:
        if qual is None:
            dept = None
            if isinstance(node, Resides_at):
                qual = qual_home
                comment.append(str(node.residence.lines[0]))
            elif isinstance(node, Works_at):
                qual = qual_work
                if node.position and node is tup[-1]:
                    comment.append(str(node.position))
                comment.append(str(node.org))
                if isinstance(node.org, Department):
                    dept = node.org
            elif isinstance(node, Department):
                dept = node
            elif isinstance(node, Has_department) and node.dept is dept:
                dept = None
                comment.append(str(node.company))
            # If we finished at a Department node, we'd better print the name
            # of the Company too.
            if dept:
                link = dept.link(incoming & is_link(Has_department))
                if link:
                    comment.append(str(link.company))
    telephones(tup[-1], tree, qual=qual, comment=', '.join(comment), **kwargs)
