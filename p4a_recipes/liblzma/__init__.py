"""
liblzma recipe — GitHub source mirror (bypasses blocked tukaani.org).
Workflow now includes 'gettext' for autopoint.
"""
from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import shprint, current_directory
from os.path import join
import sh


class LiblzmaRecipe(Recipe):
    version = '5.2.4'
    url = 'https://github.com/xz-mirror/xz/archive/refs/tags/v{version}.tar.gz'
    built_libraries = {'liblzma.so': 'src/liblzma/.libs'}
    need_stl_shared = False

    def should_build(self, arch):
        return True

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            shprint(sh.Command('autoreconf'), '-fi', _env=env)
            shprint(sh.Command('./configure'),
                    '--host=' + arch.command_prefix,
                    '--prefix=' + arch.get_build_dir(),
                    '--enable-static', '--disable-shared',
                    '--disable-xz', '--disable-xzdec',
                    '--disable-lzmadec', '--disable-lzmainfo',
                    '--disable-lzma-links', '--disable-scripts',
                    _env=env)
            shprint(sh.make, '-j' + str(self.ctx.num_cores), _env=env)
            self.install_libs(arch, join('src', 'liblzma', '.libs', 'liblzma.so'))
            self.install_include_dir(arch, 'src/liblzma/', 'lzma')


recipe = LiblzmaRecipe()
