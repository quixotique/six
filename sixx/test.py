# vim: sw=4 sts=4 et fileencoding=utf8 nomod

r'''Testing.
'''

import sys
import os
import os.path
import stat
import imp
import doctest

def run_doctest(name, search_path, recurse=False, prefix='', verbose=False):
    '''See the documentation for the L{imp} module to understand what is going
    on in here.
    '''
    # Load the module.  If the load fails on a module that was listed on the
    # command line, then treat it as a test failing.  Otherwise, if the module
    # was found during a recursive scan, treat it as though this module passed
    # its test.  In any case, don't recurse into it if it is a package.
    try:
        full_name = prefix.split('.')[:-1]
        for comp in name.split('.'):
            parent_name = '.'.join(full_name)
            full_name.append(comp)
            module_name = '.'.join(full_name)
            file, path, descr = imp.find_module(comp, search_path)
            try:
                try:
                    mod = sys.modules[module_name]
                except KeyError:
                    mod = imp.load_module(module_name, file, path, descr)
                    # Insert the loaded module into the namespace of its
                    # parent, just like the 'import' statement does.
                    if parent_name in sys.modules:
                        sys.modules[parent_name].__dict__[comp] = mod
                if descr[2] == imp.PKG_DIRECTORY:
                    search_path = mod.__path__
            finally:
                if file is not None:
                    file.close()
    except ImportError as e:
        print('%s: cannot test: %s' % (module_name, str(e)))
        return len(prefix) != 0
    # Run the doctests in the module we just loaded.
    ret = True
    if verbose:
        print(mod.__name__, mod.__file__)
    try:
        result = doctest.testmod(mod, verbose=verbose)
    except ValueError as e:
        print('%s: %s' % (module_name, e))
        ret = False
    else:
        print('%s: ran %u tests, %u failed' % (module_name,
                          result[1], result[0]))
        if result[0]:
            ret = False
    # If the --recursive option was given, and the module we loaded is in fact
    # a package, then search the package's directory for modules (and packages)
    # and test them too.
    if recurse and descr[2] == imp.PKG_DIRECTORY:
        pysuffix = dict(((mtype, suffix)
                         for suffix, mode, mtype in imp.get_suffixes()))\
                        .get(imp.PY_SOURCE)
        suffixes = [pysuffix]
        for ent in os.listdir(path):
            name = None
            if os.path.isdir(os.path.join(path, ent)):
                name = ent
            else:
                for suffix in suffixes:
                    if ent.endswith(suffix):
                        n = ent[:-len(suffix)]
                        if not (n.startswith('__') and n.endswith('__')):
                            name = n
                        break
            if name is not None:
                if not run_doctest(name, search_path, recurse=recurse,
                                   verbose=verbose,
                                   prefix=module_name + '.'):
                    ret = False
    return ret
