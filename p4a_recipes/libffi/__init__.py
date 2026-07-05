"""
libffi v3.4.6 — fix autoconf issue on Ubuntu 24.04.
The LT_SYS_SYMBOL_USCORE macro was removed in newer libtool.
"""
from os.path import exists, join
from multiprocessing import cpu_count
from pythonforandroid.recipe import Recipe
from pythonforandroid.logger import shprint
from pythonforandroid.util import current_directory
import sh


class LibffiRecipe(Recipe):
    name = 'libffi'
    version = 'v3.4.6'
    url = 'https://github.com/libffi/libffi/archive/{version}.tar.gz'
    patches = ['remove-version-info.patch']
    built_libraries = {'libffi.so': '.libs'}

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            if not exists('configure'):
                # Remove LT_SYS_SYMBOL_USCORE from configure.ac
                # (this macro doesn't exist on Ubuntu 24.04's libtool)
                shprint(sh.sed, '-i', '/LT_SYS_SYMBOL_USCORE/d', 'configure.ac', _env=env)
                shprint(sh.Command('./autogen.sh'), _env=env)
            shprint(sh.Command('autoreconf'), '-vif', _env=env)
            shprint(sh.Command('./configure'),
                    '--host=' + arch.command_prefix,
                    '--prefix=' + self.get_build_dir(arch.arch),
                    '--disable-builddir',
                    '--enable-shared', _env=env)
            shprint(sh.make, '-j', str(cpu_count()), 'libffi.la', _env=env)

    def get_include_dirs(self, arch):
        return [join(self.get_build_dir(arch), 'include')]


recipe = LibffiRecipe()
