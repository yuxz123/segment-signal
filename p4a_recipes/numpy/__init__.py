"""
numpy recipe override — adds v prefix for git checkout.
p4a's base download_file does git checkout {version}, but numpy tags are v1.26.4.
Since version is a read-only property (data descriptor), we can't monkey-patch it
even with object.__setattr__. Instead, we replicate the git download logic here.
"""
import os

from pythonforandroid.recipes.numpy import NumpyRecipe as BaseNumpyRecipe
from pythonforandroid.logger import shprint, info
from pythonforandroid.util import current_directory
import sh


class NumpyRecipe(BaseNumpyRecipe):
    def download_file(self, url, filename):
        if os.path.exists(filename):
            info(f'{filename} already exists, skipping download')
            return
        clean_url = url.replace('git+', '', 1)
        shprint(sh.git, 'clone', '--recurse-submodules', clean_url, filename)
        with current_directory(filename):
            shprint(sh.git, 'checkout', 'v' + self.version)


recipe = NumpyRecipe()
