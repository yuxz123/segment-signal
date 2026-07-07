"""
numpy recipe override — adds v prefix for git checkout.
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
