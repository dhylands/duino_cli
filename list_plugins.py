import importlib
import pkg_resources
import pkgutil

discovered_plugins = {
    name: importlib.import_module(name)
    for finder, name, ispkg
    in pkgutil.iter_modules()
    if name.startswith('duino_cli_') or name.startswith('__editable___duino_cli_')
}

for k,v in discovered_plugins.items():
    print(k, v)
    print('---------------------')
    print('v.__file__ =', v.__file__)
    print(dir(v))
    print('v.install =', v.install)
    x = v.install()
    print('x =', dir(x))

#print('-----')
#for importer, modname, ispkg in pkgutil.iter_modules():
#    print(f'Found submodule {modname} (is a package: {ispkg})')
#print('-----')

if False:
    print('=====================================')
    for pkg in pkg_resources.working_set:
        #print(pkg.project_name)
        if pkg.project_name.startswith('duino-cli-'):
            print(pkg.project_name)
            print(pkg.location)
            loader = pkg.loader
            print('loader =', loader)
            print(dir(pkg))