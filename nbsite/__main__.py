import argparse
import inspect

from .cmd import build, generate_rst, init


def _add_common_args(parser,*names):
    common = {
        '--project-root': dict(type=str,help='defaults to current working directory',default=''),
        '--examples': dict(type=str,help='if relative, should be relative to project-root',default='examples'),
        '--doc': dict(type=str,help='if relative, should be relative to project-root',default='doc'),
        '--overwrite': dict(action='store_true', help='whether to overwrite any files [DANGEROUS]')
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
    init_parser.add_argument('--theme', type=str, help='sphinx theme to use in template', choices=['holoviz', ''], default='')
    _set_defaults(init_parser,init)

    generaterst_parser = subparsers.add_parser("generate-rst", help=inspect.getdoc(generate_rst))
    _add_common_args(generaterst_parser,'--project-root','--doc','--examples', '--overwrite')
    generaterst_parser.add_argument('--project-name', type=str, help='name of project')
    generaterst_parser.add_argument('--host',type=str,help='host to use when generating notebook links',default='GitHub')
    generaterst_parser.add_argument('--org',type=str,help='github organization',default='')
    generaterst_parser.add_argument('--repo',type=str,help='name of repo',default='')
    generaterst_parser.add_argument('--branch',type=str,help='branch to point to in notebook links',default='main')
    generaterst_parser.add_argument('--offset',type=int,help='number of cells to delete from top of notebooks',default=0)
    generaterst_parser.add_argument('--nblink',type=str,help='where to place notebook links',choices=['bottom', 'top', 'both', 'none'], default='bottom')
    generaterst_parser.add_argument('--binder',type=str,help='where to place binder link',choices=['bottom', 'top', 'both', 'none'], default='none')
    generaterst_parser.add_argument('--skip',type=str,help='notebooks to skip running; comma separated case insensitive re to match',default='')
    generaterst_parser.add_argument('--keep-numbers',action='store_true',help='whether to keep the leading numbers of notebook URLs and titles')
    generaterst_parser.add_argument('--disable-interactivity-warning',action='store_true',help='whether to disable interactivity warnings')
    _set_defaults(generaterst_parser,generate_rst)

    build_parser = subparsers.add_parser("build", help=inspect.getdoc(build))
    build_parser.add_argument('--what',type=str,help='type of output to generate',default='html')
    build_parser.add_argument('--project-name', type=str, help='name of project', default='')
    build_parser.add_argument('--org',type=str,help='github organization',default='')
    build_parser.add_argument('--host',type=str,help='host to use when generating notebook links',default='GitHub')
    build_parser.add_argument('--repo',type=str,help='name of repo',default='')
    build_parser.add_argument('--branch',type=str,help='branch to point to in notebook links',default='main')
    build_parser.add_argument('--binder',type=str,help='where to place binder link',choices=['bottom', 'top', 'both', 'none'], default='none')
    build_parser.add_argument('--disable-parallel',action=argparse.BooleanOptionalAction,help='whether to disable building the docs in parallel')

    build_parser.add_argument('--output',type=str,help='where to place output',default="builtdocs")
    _add_common_args(build_parser,'--project-root','--doc','--examples', '--overwrite')
    build_parser.add_argument('--examples-assets',type=str,default="assets",
                              help='dir in which assets for examples are located - if relative, should be relative to project-root')
    build_parser.add_argument('--clean-dry-run',action='store_true',help='whether to not actually delete files from output (useful for uploading)')
    build_parser.add_argument('--inspect-links',action='store_true',help='whether to not to print all links')
    _set_defaults(build_parser,build)

    args = parser.parse_args()
    return args.func(args) if hasattr(args,'func') else parser.error("must supply command to run")

if __name__ == "__main__":
    main()
