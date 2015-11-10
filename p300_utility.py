import os

def get_feedback_directory():
	# get absolute path to this file
	abspath = os.path.abspath(globals()["__file__"])
	# get the base directory 
	return os.path.dirname(abspath)
