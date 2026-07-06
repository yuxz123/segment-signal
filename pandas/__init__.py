"""
pandas recipe override — adds v prefix for git checkout.
p4a's base download_file does git checkout {version}, but pandas tags are v1.5.3.
Since version is a read-only property (data descriptor), we can't monkey-patch it
even with object.__setattr__. Instead, we replicate the git download logic here.
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
        clean_url = url.replace('git+', '', 1)
        shprint(sh.git, 'clone', '--recurse-submodules', clean_url, filename)
        with current_directory(filename):
            shprint(sh.git, 'checkout', 'v' + self.version)


recipe = PandasRecipe()
