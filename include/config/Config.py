import os, sys, json, codecs
import re


from os.path import join, isdir
from os.path import isfile, isdir, join, basename
from pprint import pprint as pp

e=sys.exit


class Config(object): 
	print('INIT:',__file__)
	def __init__(self, **kwargs):
		self.home=None

	def LoadConfig(self, config_path, quiet=False):
		
		with codecs.open(config_path, encoding="utf-8") as stream:
			data=stream.read()
			cfg = json.loads(data)
		
		out =d2d2(cfg)
		if not quiet:
			print('-'*80)
		return out

	def saveConfig(self):
		
		#assert hasattr(self, 'cfg')
		assert isfile(self.apc_path)
		
		with open(self.apc_path, 'w') as fp:
			dump = json.dumps(self.cfg, indent='\t', separators=(',', ': '))
		   
			new_data= re.sub('"\n[\t]+},', '"},', dump)

			fp.write(dump)