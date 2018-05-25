import inspect

#sys.path.insert(0, os.path.abspath(os.path.join("..", "..", "param")))

import param

param.parameterized.docstring_signature = False
param.parameterized.docstring_describe_params = False


def param_formatter(app, what, name, obj, options, lines):
    if what == 'module':
        lines = ["start"]

    if what == 'class':
        if isinstance(obj, param.parameterized.ParameterizedMetaclass):
            params = obj.params()
            for child in params:
                if child not in ["print_level", "name"]:
                    doc = ""
                    if params[child].doc: doc = params[child].doc
                    members = inspect.getmembers(params[child])
                    params_str = ""
                    for m in members:
                        if m[0][0] != "_" and m[0] != "doc" and m[0] != "class_" and not inspect.ismethod(m[1]) and not inspect.isfunction(m[1]):
                            params_str += "%s=%s, " % (m[0], m[1])
                    params_str = params_str[:-2]
                    lines.extend(["", "*param %s* ``%s`` (*%s*)" % (params[child].__class__.__name__, child, params_str), "    %s" % doc])
