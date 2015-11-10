# 
# 	This module defines a common base class for the items that can be used to populate the matrix displayed
# 	by the feedback. 
#

import os
from p300_tasks import *
from p300_utility import *
from p300_thumbnailer import *
from glutils import GLSprite

P300_PHOTO_UNTAGGED = 0
P300_PHOTO_TAGGED = 1

class p300_item:
	def __init__(self, id):
		self.ID = id
		self.thumb = None
		self.thumb_loaded = False

	def load_thumbnail(self):
		pass

class p300_photo_item(p300_item):
	def __init__(self, id, filename, tagged):
		p300_item.__init__(self, id)
		self.filename = filename
		self.tagged = tagged

	def load_thumbnail(self):
		if self.thumb_loaded: return
		self.thumb = p300_thumbnailer.get_thumbnail_as_glsprite(self)
		self.thumb_loaded = True

	def tag(self):
		self.tagged = P300_PHOTO_TAGGED

	def untag(self):
		self.tagged = P300_PHOTO_UNTAGGED
	
	def toggle_tag(self):
		if self.tagged == P300_PHOTO_TAGGED:
			self.tagged = P300_PHOTO_UNTAGGED
		else:
			self.tagged = P300_PHOTO_TAGGED

	def is_tagged(self):
		return (self.tagged == P300_PHOTO_TAGGED)


class p300_directory_item(p300_item):
	def __init__(self, id, dirname):
		p300_item.__init__(self, id)
		self.dirname = dirname

	def load_thumbnail(self):
		if self.thumb_loaded: return
		self.thumb = GLSprite(os.path.join(get_feedback_directory(), 'gfx/folder.png'))
		self.thumb_loaded = True

class p300_action_item(p300_item):
	def __init__(self, id):
		p300_item.__init__(self, id)
		self.count = 0

	def load_thumbnail(self):
		if self.thumb_loaded: return

		# load the appropriate image based on the task ID
		if self.ID == TASK_OPEN_DIRECTORY:
			self.thumb = GLSprite(os.path.join(get_feedback_directory(), 'gfx/folder.png'))
		elif self.ID == TASK_SCROLL_LEFT:
			self.thumb = GLSprite(os.path.join(get_feedback_directory(), 'gfx/task_scrollleft.png'))
		elif self.ID == TASK_SCROLL_RIGHT:
			self.thumb = GLSprite(os.path.join(get_feedback_directory(), 'gfx/task_scrollright.png'))
		elif self.ID == TASK_CLEAR_TAGS:
			self.thumb = GLSprite(os.path.join(get_feedback_directory(), 'gfx/task_cleartags.png'))
		elif self.ID == TASK_DELETE_TAGGED:
			self.thumb = GLSprite(os.path.join(get_feedback_directory(), 'gfx/task_deletetagged.png'))
		elif self.ID == TASK_COPY_TAGGED:
			self.thumb = GLSprite(os.path.join(get_feedback_directory(), 'gfx/task_copytagged.png'))
		elif self.ID == TASK_SLIDESHOW:
			self.thumb = GLSprite(os.path.join(get_feedback_directory(), 'gfx/task_slideshow.png'))

		self.thumb_loaded = True

	def requires_confirmation(self):
		if self.ID == TASK_DELETE_TAGGED:
			return True

		return False
	
	def was_selected(self):
		self.count += 1

	def reset_count(self):
		self.count = 0

	def selected_count(self):
		return self.count
