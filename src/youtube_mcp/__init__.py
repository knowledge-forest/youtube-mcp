"""youtube-mcp — YouTube watch engine for AI agents."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("youtube-watch-mcp")
except PackageNotFoundError:  # running from source without an installed dist
    __version__ = "0.0.0+unknown"
