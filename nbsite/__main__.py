import argparse
import inspect

from .cmd import init, generate_rst, build

def _add_common_args(parser,*names):
    common = {
        '--project-root': dict(type=str,help='Defaults to current working directory',default=''),
        '--examples': dict(type=str,help='If relative, should be relative to project-root',default='examples'),
        '--doc': dict(type=str,help='If relative, should be releative to project-root',default='doc')
        }
    for name in names:
        parser.add_argument(name,**common[name])

def _set_defaults(parser,fn):
    parser.set_defaults(func=lambda args: fn( **{k: getattr(args,k) for k in vars(args) if k!='func'} ))

def main(args=None):
    parser = argparse.ArgumentParser(description="nbsite commands")
    subparsers = parser.add_subparsers(title='available commands')

    init_parser = subparsers.add_parser("init", help=inspect.getdoc(init))
    _add_common_args(init_parser,'--project-root','--doc')
    _set_defaults(init_parser,init)

    generaterst_parser = subparsers.add_parser("generate-rst", help=inspect.getdoc(generate_rst))
    _add_common_args(generaterst_parser,'--project-root','--doc','--examples')
    generaterst_parser.add_argument('--project-name',type=str,help='where to init doc',default='')
    generaterst_parser.add_argument('--host',type=str,help='where to init doc',default='GitHub')
    generaterst_parser.add_argument('--org',type=str,help='where to init doc',default='')
    generaterst_parser.add_argument('--repo',type=str,help='where to init doc',default='')
    generaterst_parser.add_argument('--branch',type=str,help='where to init doc',default='master')
    generaterst_parser.add_argument('--offset',type=int,help='where to init doc',default=0)
    generaterst_parser.add_argument('--overwrite',type=int,help='where to init doc',default=False)
    _set_defaults(generaterst_parser,generate_rst)

    build_parser = subparsers.add_parser("build", help=inspect.getdoc(build))
    build_parser.add_argument('--what',type=str,help='where to init doc',default='html')
    build_parser.add_argument('--output',type=str,help='where to init doc',default="builtdocs")
    _add_common_args(build_parser,'--project-root','--doc','--examples')
    build_parser.add_argument('--examples-assets',type=str,help='where to init doc',default="assets")    
    _set_defaults(build_parser,build)
    
    # add commands from pyct, for examples
    try:
        import pyct.cmd
        pyct.cmd.add_commands(subparsers,'nbsite',cmds=None,args=args)
    except ImportError:
        pass

    args = parser.parse_args()
    return args.func(args) if hasattr(args,'func') else parser.error("must supply command to run") 

if __name__ == "__main__":
    main()
