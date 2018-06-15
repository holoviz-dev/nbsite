import argparse
import inspect

from .cmd import init

def main(args=None):

    parser = argparse.ArgumentParser(description="nbsite commands")
    subparsers = parser.add_subparsers(title='available commands')

    init_parser = subparsers.add_parser("init", help=inspect.getdoc(init))
    init_parser.add_argument('--path',type=str,help='where to init doc',default='doc')
    init_parser.set_defaults(func=lambda args: init(path=args.path))
    
    
    # add commands from pyct, for examples
    try:
        import pyct.cmd
    except ImportError:
        import sys
        from . import _missing_cmd
        print(_missing_cmd())
        sys.exit(1)
    pyct.cmd.add_commands(subparsers,'nbsite',cmds=None,args=args)

    args = parser.parse_args()
    return args.func(args) if hasattr(args,'func') else parser.error("must supply command to run") 

if __name__ == "__main__":
    main()
