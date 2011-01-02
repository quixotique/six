# vim: sw=4 sts=4 et fileencoding=latin1 nomod

r'''Dump report.
'''

import sys
import locale
from collections import defaultdict
from itertools import chain
from six.multilang import multilang
from six.sort import *
from six.node import *
from six.node import node_predicate
from six.links import *
from six.person import *
from six.family import *
from six.org import *
from six.world import *
from six.address import *
from six.telephone import *
from six.email import *
from six.keyword import *
from six.data import *
from six.comment import *
from six.uniq import uniq

def report_dump_getopt(parser):
    lang, enc = locale.getlocale()
    parser.set_defaults(encoding=enc)
    parser.add_option('-e', '--encode',
                      action='store', type='string', dest='encoding',
                      help='use ENCODE as output encoding')

def report_dump(options, model, predicate, local):
    # If no predicate given, then select all people, organisations, and
    # families.
    if predicate is None:
        predicate = node_predicate(lambda node: True)
    # Populate the top level of the report with all the nodes that satisfy the
    # predicate.
    itemiser = Itemiser()
    itemiser.update(model.nodes(is_other(instance_p(NamedNode) & predicate)))
    # These sets control where entries are listed.
    seen = set(itemiser)
    see_in = defaultdict(set)
    alias = dict()
    # Form the sorted index of all the top-level entries in the report.
    toplevel = sorted(chain(itemiser.items(),
                            itemiser.alias_items(alias.iteritems())))
    # Remove unnecessary references.
    cull_references(toplevel)
    # Now format the report.
    from six.output import Treebuf
    tree = Treebuf(local=local)
    for item in toplevel:
        if item.node is None:
            pass
        elif item is not item.single:
            tree.nl()
            tree.add(item.key, ' -> ', item.single.key)
            tree.nl()
        elif isinstance(item.node, Person):
            tree.nl()
            dump_names(item.node, tree, name=item.key)
            dump_person(item.node, tree.sub(),
                        seen - see_in.get(item.node, set()))
        elif isinstance(item.node, Family):
            tree.nl()
            dump_names(item.node, tree, name=item.key)
            dump_family(item.node, tree.sub(),
                        seen - see_in.get(item.node, set()))
        elif isinstance(item.node, Department):
            tree.nl()
            dump_names(item.node, tree, name=item.key)
            dump_organisation(item.node, tree.sub(),
                              seen - see_in.get(item.node, set()))
        elif isinstance(item.node, Organisation):
            tree.nl()
            dump_names(item.node, tree, name=item.key)
            dump_organisation(item.node, tree.sub(),
                              seen - see_in.get(item.node, set()))
    if options.output_path:
        ofile = file(options.output_path, 'w')
    else:
        ofile = sys.stdout
    ofile.write(unicode(tree).encode(options.encoding, 'replace'))

def add_name(node, tree, context=None):
    if context is not None:
        assert isinstance(context, Link)
    if isinstance(node, NamedNode):
        # When listing a person within their family's entry, omit the name as
        # it would appear in the family entry's head.
        if isinstance(node, Person) and isinstance(context, Belongs_to):
            assert context.person is node
            names = list(node.names(with_aka=False))
            hn = node.family_head_name()
            names = [n for n in names
                       if hn != n and not hn.startswith(n + ' ')] or names
            names.extend(node.aka)
        else:
            names = list(node.names())
    else:
        names = [node]
    tree.add(names[0])
    if isinstance(node, Organisation):
        has_depts = list(node.links(incoming & is_link(Has_department)))
        assert len(has_depts) <= 1
        if has_depts:
            if has_depts[0] is not context:
                tree.add(', ')
                add_name(has_depts[0].company, tree, context)
    elif isinstance(node, Person):
        if isinstance(context, Works_at) and context.position:
            tree.add(', ', context.position)
    return names[1:]

def dump_names(node, tree, context=None, name=None):
    if name:
        tree.add(name)
        aka_names = map(unicode, node.names())
    else:
        aka_names = add_name(node, tree, context)
    tree.nl()
    if aka_names:
        tree = tree.sub()
        for aka in aka_names:
            if aka != name:
                tree.add('= ', aka)
                tree.nl()

def dump_person(per, tree, seen=frozenset(), show_family=True, show_work=True,
                show_data=True):
    dump_comments(per, tree)
    if per.birthday():
        tree.add(multilang(en='Birthday', es='F.nac.'))
        tree.add(': ')
        tree.add(per.birthday())
        tree.nl()
    telephones(per, tree)
    dump_email(per, tree)
    dump_postal(per, tree)
    dump_residences(per, tree)
    # Avoid endless recursion in dump_family() and dump_organisation().
    seen = seen | set([per])
    if show_family:
        for link in per.links(outgoing & is_link(Belongs_to)):
            refonly = link.family in seen
            if refonly:
                tree.add('-> ')
                tree.add(link.family.sort_keys().next())
            else:
                tree.add('-- ')
                add_name(link.family, tree, link)
            tree.nl()
            sub = tree.sub()
            dump_comments(link, sub)
            telephones(link, sub)
            dump_email(link, sub)
            if not refonly:
                dump_family(link.family, sub, seen,
                            show_members=False, show_data=False)
    if show_work:
        for link in per.links(outgoing & is_link(Works_at)):
            refonly = link.org in seen
            if refonly:
                tree.add('-> ')
            else:
                tree.add('-- ')
            if link.position:
                tree.add(link.position, ', ')
            if refonly:
                tree.add(link.org.sort_keys().next())
            else:
                add_name(link.org, tree, link)
            tree.nl()
            sub = tree.sub()
            dump_comments(link, sub)
            telephones(link, sub)
            dump_email(link, sub)
            dump_postal(link, sub)
            if not refonly:
                dump_organisation(link.org, sub, seen,
                                  show_workers=False, show_data=False)
    if show_data:
        dump_data(per, tree)

def dump_family(fam, tree, seen=frozenset(), show_members=True, show_data=True):
    # Avoid endless recursion in dump_person().
    seen = seen | set([fam])
    dump_comments(fam, tree)
    dump_residences(fam, tree)
    telephones(fam, tree)
    dump_email(fam, tree)
    dump_postal(fam, tree)
    if show_data:
        dump_data(fam, tree)
    if show_members:
        for link in sorted(fam.links(incoming & is_link(Belongs_to)),
                           key=lambda l: (not l.is_head,
                                          l.sequence or 0,
                                          l.person.sortkey())):
            if link.person in seen:
                tree.add('-> ')
                tree.add(link.person.sort_keys().next())
                tree.nl()
                sub = tree.sub()
                dump_comments(link, sub)
                telephones(link, sub)
                dump_email(link, sub)
            else:
                tree.add('-- ')
                dump_names(link.person, tree, link)
                sub = tree.sub()
                dump_comments(link, sub)
                telephones(link, sub)
                dump_email(link, sub)
                dump_person(link.person, sub, seen, show_family=False,
                            show_data=show_data)

def dump_organisation(org, tree, seen=frozenset(), show_workers=True,
                      show_data=True):
    # Avoid endless recursion in dump_works_at() and dump_organisation().
    seen = seen | set([org])
    dump_comments(org, tree)
    telephones(org, tree)
    dump_email(org, tree)
    dump_postal(org, tree)
    dump_residences(org, tree)
    if show_workers:
        dump_works_at(org, tree, seen)
    if show_data:
        dump_data(org, tree)
    for link in org.links(outgoing & is_link(Has_department)):
        refonly = link.dept in seen
        if refonly:
            tree.add('-> ')
            tree.add(link.dept.sort_keys().next())
            tree.nl()
        else:
            dump_names(link.dept, tree, link)
        sub = tree.sub()
        dump_comments(link, sub)
        if not refonly:
            dump_organisation(link.dept, sub, seen, show_workers=show_workers,
                              show_data=show_data)

qual_home = multilang(en='home', es='casa')
qual_work = multilang(en='work', es='trab')

def dump_works_at(org, tree, seen):
    assert org in seen
    for link in sorted(org.links(incoming & is_link(Works_at))):
        refonly = link.person in seen
        if refonly:
            tree.add('-> ')
            tree.add(link.person.sort_keys().next())
            if link.position:
                tree.add(', ', link.position)
            tree.nl()
        else:
            tree.add('-- ')
            dump_names(link.person, tree, link)
        sub = tree.sub()
        dump_comments(link, sub)
        telephones(link, sub)
        dump_email(link, sub)
        dump_postal(link, sub)
        if not refonly:
            dump_person(link.person, sub, seen, show_work=False, show_data=False)
        dump_data(link, sub)

def dump_email(who, tree):
    for link in who.links(outgoing & is_link(Has_email)):
        if isinstance(link, At_work):
            tree.add(unicode(qual_work).capitalize(), ': ')
        elif isinstance(link, At_home):
            tree.add(unicode(qual_home).capitalize(), ': ')
        tree.set_wrapmargin()
        tree.add(link.email)
        wrap_comments(link.email, tree)
        wrap_comments(link, tree)
        tree.nl()

def wrap_comments(node, tree):
    comment = getattr(node, 'comment', None)
    if comment:
        tree.wrap('; ', comment)

def telephones(who, tree, qual=None, comment=None, bold=False,
               mobile=True, fixed=True, fax=True):
    typs = []
    if mobile:
        typs.append(Has_mobile)
    if fixed:
        typs.append(Has_fixed)
    if fax:
        typs.append(Has_fax)
    for typ in typs:
        for link in who.links(outgoing & is_link(typ)):
            telephone(link, tree, qual=qual, comment=comment, bold=bold)
            tree.nl()

def telephone(link, tree, qual=None, comment=None, bold=False):
    if isinstance(link, Has_mobile):
        tree.add(multilang(en='Mob', es=u'Móv'))
    elif isinstance(link, Has_fax):
        tree.add(u'Fax')
    else:
        assert isinstance(link, Has_fixed)
        tree.add(multilang(en='Tel', es=u'Tlf'))
    if qual:
        tree.add(' ', qual)
    elif isinstance(link, At_work):
        tree.add(' ', qual_work)
    elif isinstance(link, At_home):
        tree.add(' ', qual_home)
    tree.add(': ')
    tree.set_wrapmargin()
    tree.add(link.tel.relative(tree.local), bold=bold)
    wrap_comments(link.tel, tree)
    wrap_comments(link, tree)
    if comment:
        tree.wrap(' -- ', comment)

def dump_postal(who, tree):
    for link in who.links(outgoing & is_link(Has_postal_address)):
        tree.add(link.postal)
        tree.nl()
        sub = tree.sub()
        dump_comments(link, sub)
        dump_comments(link.postal, sub)

def dump_residences(who, tree):
    for link in who.links(outgoing & is_link(Resides_at)):
        tree.add(link.residence.relative(tree.local))
        tree.nl()
        sub = tree.sub()
        dump_comments(link, sub)
        telephones(link, sub)
        dump_comments(link.residence, sub)
        telephones(link.residence, sub)

def dump_data(who, tree):
    others = {}
    for link in who.links(is_link(With) | (outgoing & is_link(Is_in))):
        other = link.other(who)
        agent = None
        if isinstance(other, Works_at):
            agent = other.person, other.position
            other = other.org
        position = getattr(link, 'position', None)
        key = (isinstance(link, Is_in), other, position, agent)
        if key not in others:
            others[key] = []
        others[key].append(link)
    keys = others.keys()
    keys.sort(key=lambda k: (not k[0], unicode(k[1]), unicode(k[2])))
    for key in keys:
        (is_in, other, position, agent) = key
        links = others[key]
        tree.add('* ')
        if position and isinstance(other, Organisation):
            tree.add(position, ', ')
            position = None
        if is_in:
            tree.add('in ')
        tree.add(other)
        if position:
            tree.add(', ', position)
        if agent:
            person, position = agent
            tree.add(' (')
            sub.add(person)
            if position:
                sub.add(", ")
                sub.add(position)
            tree.add(')')
        tree.nl()
        for link in links:
            sub = tree.sub()
            dump_comments(link, sub)
            data = list(link.nodes(incoming & is_link(Has_context)))
            data.sort(key=unicode)
            for datum in data:
                sub.add(datum)
                sub.nl()
                dump_comments(datum, sub.sub())

def dump_comments(node, tree):
    for com in node.nodes(outgoing & is_link(Has_comment)):
        tree.add('; ')
        tree.set_wrapmargin()
        tree.wrap(unicode(com))
        tree.nl()

