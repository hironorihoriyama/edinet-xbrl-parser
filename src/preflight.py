"""Simple environment check for required dependencies."""

import sys
import inspect

print("Python:", sys.version)
import arelle
print("arelle:", inspect.getfile(arelle))
from lxml import etree
print("lxml:", etree.LIBXML_VERSION)
import regex
print("regex:", regex.__version__)
import PIL
import importlib
importlib.import_module("PIL._imaging")
print("pillow OK")
print("[OK] preflight passed")

