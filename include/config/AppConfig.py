import os, re, sys, copy, string, logging 
from os.path import isfile, isdir, join, basename, dirname
import json
from datetime import datetime 
from copy import deepcopy
from pprint import pprint as pp
from include.config.Config import Config
import shutil
import logging

log=logging.getLogger()

e=sys.exit
from collections import defaultdict


class Counter(object):
	def __init__(self):
		self.cnt=defaultdict(int) #(lambda: 1)
	def inc(self, obj):
		#tname=obj.__class__.__name__
		tname=f'{obj.fname}.{obj.__class__.__name__}'.replace('.','_')
		self.cnt[tname] +=1
	def get(self, obj):
		#tname=obj.__class__.__name__
		tname=f'{obj.fname}.{obj.__class__.__name__}'.replace('.','_')
		return self.cnt[tname]
		

class AppConfig(Config): 
	def __init__(self):
		
		self.gid=0
		self.cntr = Counter()
		self.all={}
	def init(self, **kwargs):
		Config.__init__(self,**kwargs)
		if 0:
			self.kwargs=kwargs
			self.ui_layout=kwargs['ui_layout']

	def get_gid(self, obj):
		self.gid += 1
		self.all[self.gid] = obj
		return self.gid
	def load_ui_cfg(self, quiet=False):


		self.ucfg = self.LoadConfig(config_path=self.apc_path, quiet=quiet)
		assert self.ucfg is not None, self.ucfg
		return self

	def getErrDlgSize(self):
		cfg=self.cfg
		assert 'ErrDlg' in cfg
		assert 'size' in cfg['ErrDlg']
		return cfg['ErrDlg']['size']
	def getErrDlgSPos(self):
		cfg=self.cfg
		assert 'ErrDlg' in cfg
		assert 'pos' in cfg['ErrDlg']
		return cfg['ErrDlg']['pos']
	def setErrDlgSize(self, size):
		cfg=self.cfg
		assert 'ErrDlg' in cfg
		assert 'size' in cfg['ErrDlg']
		cfg['ErrDlg']['size'] = tuple(size)
		self.saveConfig()
	def setErrDlgPos(self, pos):
		cfg=self.cfg
		assert 'ErrDlg' in cfg
		assert 'pos' in cfg['ErrDlg']
		cfg['ErrDlg']['pos']= tuple(pos)
		self.saveConfig()		
		
		
		
			