import inspect

import param

param.parameterized.docstring_signature = False
param.parameterized.docstring_describe_params = False


def param_formatter(app, what, name, obj, options, lines):
    if what == 'module':
        lines = ["start"]

    if what == 'class' and isinstance(obj, param.parameterized.ParameterizedMetaclass):
        params = obj.params()
        for child in params:
            if child in ["print_level", "name"]:
                continue
            pobj = params[child]
            try:
                default = type(pobj)()
            except:
                default = None
            doc = pobj.doc or ""
            members = inspect.getmembers(pobj)
            params_str = ""
            for m in members:
                if (m[0][0] != "_" and m[0] in ("default", "bounds", "objects", "length", "step") and
                    not inspect.ismethod(m[1]) and not inspect.isfunction(m[1]) and m[1] is not None and
                    getattr(default, m[0], None) != m[1]):
                    params_str += "%s=%s, " % (m[0], repr(m[1]))
            params_str = params_str[:-2]
            ptype = params[child].__class__.__name__
            if params_str.lstrip():
                lines.extend(["", "``%s`` = param.%s(%s)" % (child, ptype, params_str), "    %s" % doc])
            else:
                lines.extend(["", "``%s`` = param.%s()" % (child, ptype), "    %s" % doc])
