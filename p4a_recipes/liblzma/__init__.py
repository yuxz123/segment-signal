"""
liblzma recipe — GitHub source mirror (bypasses blocked tukaani.org).
Workflow now includes 'gettext' for autopoint.
"""
from pythonforandroid.recipe import Recipe
from pythonforandroid.toolchain import shprint, current_directory
from os.path import join
from multiprocessing import cpu_count
import sh


class LiblzmaRecipe(Recipe):
    version = '5.2.4'
    url = 'https://github.com/xz-mirror/xz/archive/refs/tags/v{version}.tar.gz'
    built_libraries = {'liblzma.so': 'src/liblzma/.libs'}
    need_stl_shared = False

    def get_library_includes(self, arch):
        return ' -I' + join(self.get_build_dir(arch.arch), 'src', 'liblzma')

    def should_build(self, arch):
        return True

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            env['AUTOPOINT'] = '/bin/true'  # skip autopoint (gettext not installed)
            # Suppress gettext: remove po from SUBDIRS + create dummy Makefile
            shprint(sh.Command('mkdir'), '-p', 'build-aux', 'po', _env=env)
            shprint(sh.Command('touch'), 'build-aux/config.rpath', _env=env)
            shprint(sh.sed, '-i', '/^SUBDIRS/s/po//g', 'Makefile.am', _env=env)
            with open('po/Makefile.in.in', 'w') as f:
                f.write('all:\ninstall:\nclean:\n')
            shprint(sh.Command('autoreconf'), '-fi', _env=env)
            shprint(sh.Command('./configure'),
                    '--host=' + arch.command_prefix,
                    '--prefix=' + self.get_build_dir(arch.arch),
                    '--disable-nls',
                    '--enable-static', '--enable-shared',
                    '--disable-xz', '--disable-xzdec',
                    '--disable-lzmadec', '--disable-lzmainfo',
                    '--disable-lzma-links', '--disable-scripts',
                    _env=env)
            shprint(sh.make, '-j' + str(cpu_count()), _env=env)
            self.install_libs(arch, join('src', 'liblzma', '.libs', 'liblzma.so'))


recipe = LiblzmaRecipe()
