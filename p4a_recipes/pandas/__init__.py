"""
pandas recipe override — adds v prefix for git checkout.
"""
import os

from pythonforandroid.recipes.pandas import PandasRecipe as BasePandasRecipe
from pythonforandroid.logger import shprint, info
from pythonforandroid.util import current_directory
import sh


class PandasRecipe(BasePandasRecipe):
    def download_file(self, url, filename):
        if os.path.exists(filename):
            info(f'{filename} already exists, skipping download')
            return
        shprint(sh.git, 'clone', '--recurse-submodules', url, filename)
        with current_directory(filename):
            shprint(sh.git, 'checkout', 'v' + self.version)


recipe = PandasRecipe()
