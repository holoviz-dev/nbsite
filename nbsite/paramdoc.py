import inspect

from functools import partial

import param

from param.parameterized import label_formatter

param.parameterized.docstring_signature = False
param.parameterized.docstring_describe_params = False

# Parameter attributes which are never shown
IGNORED_ATTRS = [
    'precedence', 'check_on_set', 'instantiate', 'pickle_default_value',
    'watchers', 'compute_default_fn', 'doc', 'owner', 'per_instance',
    'is_instance', 'name', 'time_fn', 'time_dependent'
]

# Default parameter attribute values (value not shown if it matches defaults)
DEFAULT_VALUES = {'allow_None': False, 'readonly': False, 'constant': False}


def param_formatter(app, what, name, obj, options, lines):
    if what == 'module':
        lines = ["start"]

    if what == 'class' and isinstance(obj, param.parameterized.ParameterizedMetaclass):

        parameters = ['name']
        mro = obj.mro()[::-1]
        inherited = []
        for cls in mro[:-1]:
            if not issubclass(cls, param.Parameterized) or cls is param.Parameterized:
                continue
            cls_params = [p for p in cls.param if p not in parameters and
                          cls.param[p] == obj.param[p]]
            if not cls_params:
                continue
            parameters += cls_params
            cname = cls.__name__
            module = cls.__module__
            inherited.extend(['', '    :class:`{module}.{name}`: {params}'.format(
                name=cname, module=module, params=', '.join(cls_params))
            ])
        if inherited:
            lines.extend(["Parameters inherited from: "]+inherited)

        params = [p for p in obj.param if p not in parameters]
        for child in params:
            if child in ["print_level", "name"]:
                continue
            pobj = obj.param[child]
            label = label_formatter(pobj.name)
            doc = pobj.doc or ""
            members = inspect.getmembers(pobj)
            params_str = ""
            for name, value in members:
                try:
                    is_default = bool(DEFAULT_VALUES.get(name) == value)
                except Exception:
                    is_default = False
                skip = (
                    name.startswith('_') or
                    name in IGNORED_ATTRS or
                    inspect.ismethod(value) or
                    inspect.isfunction(value) or
                    value is None or
                    is_default or
                    (name == 'label' and pobj.label != label)
                )
                if not skip:
                    params_str += "%s=%s, " % (name, repr(value))
            params_str = params_str[:-2]
            ptype = pobj.__class__.__name__
            if params_str.lstrip():
                lines.extend(["", "``%s`` = param.%s(%s)" % (child, ptype, params_str), "    %s" % doc])
            else:
                lines.extend(["", "``%s`` = param.%s()" % (child, ptype), "    %s" % doc])


def param_skip(app, what, name, obj, skip, options):
    if what == 'class' and not skip:
        return (
            getattr(obj, '__qualname__', '').startswith('Parameters.deprecate') or
            (isinstance(obj, partial) and obj.args and isinstance(obj.args[0], param.Parameterized)) or
            (getattr(obj, '__qualname__', '').startswith('Parameterized.') and
             getattr(obj, '__class__', str).__name__ == 'function')
        )
