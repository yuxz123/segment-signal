"""
pandas recipe override — adds v prefix for git checkout.
p4a's base download_file does git checkout {version}, but pandas tags are v1.5.3.
"""
from pythonforandroid.recipes.pandas import PandasRecipe as BasePandasRecipe


class PandasRecipe(BasePandasRecipe):
    def download_file(self, url, filename):
        # git tags have v prefix: temporarily patch version for checkout only
        orig = self.version
        self.version = 'v' + orig
        try:
            super().download_file(url, filename)
        finally:
            self.version = orig


recipe = PandasRecipe()
