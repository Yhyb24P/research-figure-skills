from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("research-figure-skills")
except PackageNotFoundError:
    __version__ = "2.1.0rc1"
