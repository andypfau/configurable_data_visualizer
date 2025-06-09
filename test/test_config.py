import os, sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname('.'), 'src')))

from lib.config import Config
import polars


c = Config()
print(hash(c))
c.columns = ['a']
print(hash(c))
