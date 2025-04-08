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
    'is_instance', 'name', 'time_fn', 'time_dependent', 'rx'
]

# Default parameter attribute values (value not shown if it matches defaults)
DEFAULT_VALUES = {'allow_None': False, 'readonly': False, 'constant': False, 'allow_refs': False, 'nested_refs': False}


def param_formatter(app, what, name, obj, options, lines):
    if what == 'module':
        lines = ["start"]

    if what == 'class' and isinstance(obj, param.parameterized.ParameterizedMetaclass):
        lines.extend(['', '**Parameter Definitions**', '', '-------', ''])
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
            inherited.extend(['', f"    :class:`{module}.{cname}`: {', '.join(cls_params)}"])
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
                lines.extend(["", f"``{child} = {ptype}({params_str})``", f"    {doc}"])
            else:
                lines.extend(["", f"``{child} = {ptype}()``", f"    {doc}"])

def param_skip(app, what, name, obj, skip, options):
    if what == 'class' and not skip:
        return (
            getattr(obj, '__qualname__', '').startswith('Parameters.deprecate') or
            (isinstance(obj, partial) and obj.args and isinstance(obj.args[0], param.Parameterized)) or
            (getattr(obj, '__qualname__', '').startswith('Parameterized.') and
             getattr(obj, '__class__', str).__name__ == 'function')
        )
    elif what == 'module' and not skip and isinstance(obj, type) and issubclass(obj, param.Parameterized):
        # HACK: Sphinx incorrectly labels this as a module level discovery
        #       We abuse this skip callback to exclude parameters and
        #       include all methods
        members = [member for member in dir(obj) if not member.startswith('_') and member not in obj.param]
        if isinstance(options['members'], list):
            options['members'] += members
        else:
            options['members'] = members
        return skip
