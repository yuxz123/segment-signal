"""
numpy recipe override — adds v prefix for git checkout.
p4a's base download_file does git checkout {version}, but numpy tags are v1.26.4.
"""
from pythonforandroid.recipes.numpy import NumpyRecipe as BaseNumpyRecipe


class NumpyRecipe(BaseNumpyRecipe):
    def download_file(self, url, filename):
        # git tags have v prefix: version is a read-only property,
        # so use object.__setattr__ to bypass the descriptor.
        orig = self.version
        object.__setattr__(self, 'version', 'v' + orig)
        try:
            super().download_file(url, filename)
        finally:
            object.__setattr__(self, 'version', orig)


recipe = NumpyRecipe()
