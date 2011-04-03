import imp
import operator
import os
from pkgutil import ImpLoader

from celery.loaders import LOADER_ALIASES, default
from ZConfig.datatypes import DottedNameConversion
from zope.pagetemplate.pagetemplatefile import PageTemplateFile
from zope.tales import engine, pythonexpr, tales


LOADER_ALIASES['plone'] = 'plone.app.celery.config.ZConfigLoader'


component_xml = PageTemplateFile('component.zpt')


class ComponentXMLGenerator(ImpLoader):
    """Class generating a component.xml file on the fly
    
    ZConfig insists on loading a component.xml file from a package, but we
    want to generate this on-the-fly from celery configuration structures.
    
    Lucky for us ZConfig will use PEP 302 module hooks to load this file,
    and this class implements a get_data hook to intercept the component.xml
    loading and give us a point to generate it.
    
    """
    def __init__(self, module):
        name = module.__name__
        path = os.path.dirname(module.__file__)
        description = ('', '', imp.PKG_DIRECTORY)
        ImpLoader.__init__(self, name, None, path, description)

    def get_data(self, pathname):
        if os.path.split(pathname) == (self.filename, 'component.xml'):
            # Use our loader if no celery loader has been defined yet
            os.environ.setdefault('CELERY_LOADER', 'plone')
            from celery.app.defaults import NAMESPACES
            return component_xml(view=CeleryNamespacesComponents(NAMESPACES))
        return ImpLoader.get_data(self, pathname)


def fmt_timedelta(td):
    """Convert a timedelta to a string accepted by ZConfig"""
    res = []
    if td.days:
        res.append('%dd' % td.days)
    if td.seconds:
        hours, remainder = divmod(td.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if td.microseconds:
            seconds += td.microseconds / 10.0**6
        if hours:
            res.append('%dh' % hours)
        if minutes:
            res.append('%dm' % minutes)
        if seconds:
            # Format as float with insignificant 0s removed, and as decimal
            # if there are no microseconds. Just like %g without the exponent
            # formatting for numbers < 10**-4.
            res.append(('%.6fs' % seconds).rstrip('0.'))
    return ' '.join(res)


class CeleryNamespacesComponents(object):
    def __init__(self, namespaces):
        self.namespaces = namespaces
    
    # Map celery option type to additional info keys. map_default is applied
    # to the celery default to make a ZConfig default string.
    # Keys can also be option names to give these different type information.
    # Adding "element='multikey'" turns the option into a <multikey> item instead, 
    # with the default values as contained <default> keys.
    optionmap = dict(
        bool=dict(datatype='boolean'),
        int=dict(datatype='integer'),
        float=dict(datatype='float'),
        str=dict(datatype='string'),
        string=dict(datatype='string'),
        tuple=dict(element='multikey', datatype='string'),
        ADMINS=dict(element='multikey', datatype='.commaseparatedlist'),
        HOST=dict(datatype='ipaddr-or-hostname'),
        IMPORTS=dict(element='multikey', datatype='dotted-name'),
        PORT=dict(datatype='port-number'),
        ROUTES=dict(element='multikey', datatype='.route'),
        TASK_ERROR_WHITELIST=dict(element='multikey', datatype='dotted-name'),
        TASK_RESULT_EXPIRES=dict(datatype='timedelta',
            map_default=fmt_timedelta),
    )

    def sectiontypes(self):
        items = self.namespaces.items()
        items.sort(key=operator.itemgetter(0))
        for key, value in items:
            if isinstance(value, dict):
                name = key.lower().replace('_', '-')
                subitems = value.items()
                subitems.sort(key=operator.itemgetter(0))
                for subkey, option in subitems:
                    if option.type != 'dict':
                        continue
                    # Special case: Option(type='dict') is defined as a nested
                    # section backed with a ZConfig.basic.mapping datatype. We
                    # accept arbitrary python expressions for sections without
                    # defaults, if there are defaults they are converted to
                    # explicit keys with defaults and settings.
                    subname = subkey.lower().replace('_', '-')
                    yield dict(
                        namespace=(key, subkey),
                        name=subname,
                        extends='ZConfig.basic.mapping',
                        keytype='string',
                        datatype=(
                            option.default 
                            and '.map_with_defaults'
                            or '.python_expr_dict'
                        ),
                    )

                yield dict(
                    namespace=key,
                    name=name,
                )
        yield dict(
            namespace=None,
            name='celery-config', 
            datatype='.CeleryConfigurationSection',
            implements='zope.product.base',
        )

    def keys(self, namespace=None):
        items = self.namespaces

        if isinstance(namespace, tuple):
            # A dict option, list defaults
            namespace, optionname = namespace
            if namespace:
                items = items[namespace]
            defaultvalue = items[optionname].default
            if not defaultvalue:
                return
            for key, default in defaultvalue.items():
                # Only detects integers and floats, the rest is interpreted
                # as strings.
                yield dict(
                    name=key.replace('_', '-'),
                    element='key',
                    attribute=key,
                    datatype=(
                        isinstance(default, int) and 'integer' or
                        isinstance(default, float) and 'float' or
                        'string'),
                    default=default,
                )
            return

        # A namespace, list options
        if namespace:
            items = items[namespace]
        items = items.items()
        items.sort(key=operator.itemgetter(0))
        for key, option in items:
            name = key.lower().replace('_', '-')
            if isinstance(option, dict):
                yield dict(
                    name=key,
                    type=name,
                    element='section',
                )
            elif option.type == 'dict':
                # Link back to the special mapping sections generated above.
                info = dict(
                    name=key,
                    element='section',
                    type=name,
                )
                yield info
            else:
                # Option, rendered as ZConfig key.
                info = dict(
                    name=name,
                    attribute=key,
                    element='key',
                    default=option.default,
                )
                if key in self.optionmap:
                    info.update(self.optionmap[key])
                elif option.type in self.optionmap:
                    info.update(self.optionmap[option.type])
                if 'map_default' in info:
                    info['default'] = info['map_default'](info['default'])
                    del info['map_default']
                yield info


_econtext = tales.Context(engine.Engine, {})
def route(val):
    # Either accept a dotted name or a python expression
    try:
        return DottedNameConversion()(val)
    except ValueError:
        try:
            result = pythonexpr.PythonExpr('', val, engine.Engine)(_econtext)
            if not isinstance(result, dict):
                raise ValueError
        except:
            raise ValueError('Not a dotted name or python dict: %r' % val)
        return result


def python_expr_dict(val):
    """A dictionary with python expression values

    Used as a datatype for ZConfig.components.basic.mapping.xml sections.

    """
    d = val.mapping
    eng = engine.Engine
    for key in d:
        try:
            d[key] = pythonexpr.PythonExpr('', d[key], eng)(_econtext)
        except:
            raise ValueError('Not a valid python expression: %r' % d[key])
    return val.mapping


def map_with_defaults(val):
    """A dictionary with default values defined

    Used as a datatype for ZConfig.components.basic.mapping.xml sections,
    with additional keys defined. Every section attribute not named 'mapping'
    will be added to 'mapping' (which is turned into the section value).

    """
    d = val.mapping
    for attr in val._attributes:
        if attr == 'mapping':
            continue
        d[attr] = getattr(val, attr)
    return d


def commaseparatedlist(val):
    return [v.strip() for v in val.split(',')]


_zconfig_config = None


class CeleryConfigurationSection(object):
    def __init__(self, config):
        global _zconfig_config
        self.cfg = _zconfig_config = {}
        for namespace in config._attributes:
            subconfig = getattr(config, namespace)
            if subconfig is None:
                continue

            if not isinstance(subconfig, config.__class__):
                # not a namespace but a regular attribute
                self.cfg[namespace] = subconfig
                continue

            for name in subconfig._attributes:
                key = '%s_%s' % (namespace, name)
                value = getattr(subconfig, name)
                self.cfg[key] = value
        

    def getSectionName(self):
        return 'celery'


class ZConfigLoader(default.Loader):
    def read_configuration(self):
        """Read configuration from :file:`celeryconfig.py` and configure
        celery and Django so it can be used by regular Python."""
        global _zconfig_config
        if _zconfig_config is None:
            default.warnings.warn(default.NotConfigured(
                "No celery configuration found! Please add it to your "
                "zope.conf file."))
            return self.setup_settings(default.DEFAULT_UNCONFIGURED_SETTINGS)
        else:
            self.configured = True
            return self.setup_settings(_zconfig_config)
