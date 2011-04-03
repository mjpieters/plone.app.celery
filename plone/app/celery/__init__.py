import sys
from config import ComponentXMLGenerator
# Hook into the PEP 302 loader
__loader__ = ComponentXMLGenerator(sys.modules[__name__])
