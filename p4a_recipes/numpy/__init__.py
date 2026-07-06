"""
numpy recipe override — adds v prefix for git checkout.
p4a's base download_file does git checkout {version}, but numpy tags are v1.26.4.
"""
from pythonforandroid.recipes.numpy import NumpyRecipe as BaseNumpyRecipe


class NumpyRecipe(BaseNumpyRecipe):
    def download_file(self, url, filename):
        # git tags have v prefix: temporarily patch version for checkout only
        orig = self.version
        self.version = 'v' + orig
        try:
            super().download_file(url, filename)
        finally:
            self.version = orig


recipe = NumpyRecipe()
