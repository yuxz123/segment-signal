"""
OpenSSL recipe — GitHub mirror override.
Original downloads from openssl.org which is blocked in GitHub Actions.
"""
from os.path import join
from multiprocessing import cpu_count

from pythonforandroid.recipe import Recipe
from pythonforandroid.util import current_directory
from pythonforandroid.logger import shprint
import sh


class OpenSSLRecipe(Recipe):
    version = '3.3.1'
    # CHANGED: use GitHub releases instead of blocked openssl.org
    url = 'https://github.com/openssl/openssl/releases/download/openssl-{version}/openssl-{version}.tar.gz'

    built_libraries = {
        'libcrypto.so': '.',
        'libssl.so': '.',
    }

    def get_build_dir(self, arch):
        return join(
            self.get_build_container_dir(arch), self.name + self.version[0]
        )

    def include_flags(self, arch):
        openssl_includes = join(self.get_build_dir(arch.arch), 'include')
        return (' -I' + openssl_includes +
                ' -I' + join(openssl_includes, 'openssl'))

    def link_dirs_flags(self, arch):
        return ' -L' + self.get_build_dir(arch.arch)

    def link_libs_flags(self):
        return ' -lcrypto -lssl'

    def link_flags(self, arch):
        return self.link_dirs_flags(arch) + self.link_libs_flags()

    def get_recipe_env(self, arch=None):
        env = super().get_recipe_env(arch)
        env['OPENSSL_VERSION'] = self.version[0]
        env['CC'] = 'clang'
        env['ANDROID_NDK_ROOT'] = self.ctx.ndk_dir
        env["PATH"] = f"{self.ctx.ndk.llvm_bin_dir}:{env['PATH']}"
        env["CFLAGS"] += " -Wno-macro-redefined"
        env["MAKE"] = "make"
        return env

    def select_build_arch(self, arch):
        aname = arch.arch
        if 'arm64' in aname:
            return 'android-arm64'
        if 'v7a' in aname:
            return 'android-arm'
        if 'arm' in aname:
            return 'android'
        if 'x86_64' in aname:
            return 'android-x86_64'
        if 'x86' in aname:
            return 'android-x86'
        return 'linux-armv4'

    def build_arch(self, arch):
        env = self.get_recipe_env(arch)
        with current_directory(self.get_build_dir(arch.arch)):
            perl = sh.Command('perl')
            buildarch = self.select_build_arch(arch)
            config_args = [
                'shared',
                'no-dso',
                'no-asm',
                'no-tests',
                buildarch,
                '-D__ANDROID_API__={}'.format(self.ctx.ndk_api),
            ]
            shprint(perl, 'Configure', *config_args, _env=env)
            shprint(sh.make, '-j', str(cpu_count()), _env=env)


recipe = OpenSSLRecipe()
