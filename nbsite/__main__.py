import argparse
import inspect

from .cmd import init, generate_rst, build

def main(args=None):

    parser = argparse.ArgumentParser(description="nbsite commands")
    subparsers = parser.add_subparsers(title='available commands')

    init_parser = subparsers.add_parser("init", help=inspect.getdoc(init))
    init_parser.add_argument('--path',type=str,help='where to init doc',default='doc')
    init_parser.set_defaults(func=lambda args: init(path=args.path))

    generaterst_parser = subparsers.add_parser("generate-rst", help=inspect.getdoc(generate_rst))
    generaterst_parser.add_argument('--project',type=str,help='where to init doc',default='pyviz')
    generaterst_parser.add_argument('--org',type=str,help='where to init doc',default='pyviz')
    generaterst_parser.add_argument('--repo',type=str,help='where to init doc',default='pyviz')
    generaterst_parser.add_argument('--examples-path',type=str,help='where to init doc',default='examples')
    generaterst_parser.add_argument('--doc-path',type=str,help='where to init doc',default='doc')
    generaterst_parser.add_argument('--offset',type=int,help='where to init doc',default=0)
    generaterst_parser.add_argument('--overwrite',type=int,help='where to init doc',default=False)
    
    generaterst_parser.set_defaults(func=lambda args: generate_rst(project=args.project,examples_path=args.examples_path,doc_path=args.doc_path,git_org=args.org,git_repo=args.repo,offset=args.offset,overwrite=args.overwrite))

    build_parser = subparsers.add_parser("build", help=inspect.getdoc(build))
    build_parser.add_argument('--what',type=str,help='where to init doc',default='html')
    build_parser.add_argument('--examples-path',type=str,help='where to init doc',default='examples')
    build_parser.add_argument('--doc-path',type=str,help='where to init doc',default='doc')
    build_parser.add_argument('--output',type=str,help='where to init doc',default="builtdocs")
    build_parser.add_argument('--assets',type=str,help='where to init doc',default="assets")    
    build_parser.set_defaults(func=lambda args: build(args.what,args.examples_path,args.doc_path,args.output,args.assets))
    
    
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
