from include.config.AppConfig import AppConfig

def init(**kwargs):
	global apc

	apc = AppConfig(**kwargs)