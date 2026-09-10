"""json_dump -- flatten, convert and merge arbitrary nested data structures.

One line per leaf, so a document becomes something grep, less, cut and awk
can read -- including a minified one with no newlines in it at all.  The
default notation and ``--perl-compat`` come from the Perl script this package
grew out of; the rest of the catalogue (python, javascript, go, r, jq, and any
a user writes) lives in :mod:`json_dump.templates`, and a pluggable set of
optional serialisation formats turns the same walk into a converter.
"""

__version__ = "0.2.0"
__author__ = "Jeremy Melanson"

__all__ = ["__author__", "__version__"]
