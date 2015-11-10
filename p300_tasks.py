# 
#
#

# Each task must have a unique ID < 0 (to avoid clashing with photo IDs which are positive)
TASK_SCROLL_LEFT 				= -1
TASK_SCROLL_RIGHT 				= -2
TASK_CLEAR_TAGS 				= -3
TASK_DELETE_TAGGED 				= -4
TASK_COPY_TAGGED				= -5
TASK_SLIDESHOW 					= -6
TASK_OPEN_DIRECTORY 			= -7
TASK_DISPLAY_SELECTION 			= -8

from p300_config import *
from p300_thumbnailer import *
from p300_items import *

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from glutils import *

from shutil import copyfile
from time import sleep

class p300_task:
	def __init__(self, id):
		self.ID = id
		self.nextstate = -1

	# Override if required
	def requires_confirmation(self):
		return False

	def is_complex(self):
		return False

	# Override!
	def perform_task(self, data):
		pass

	# Override!
	def get_result(self):
		pass

	def set_next_state(self, ns):
		self.nextstate = ns

	def restore_state(self):
		return self.nextstate

class p300_complex_task(p300_task):
	def __init__(self, id):
		p300_task.__init__(self, id)
		self.elapsed = 0

	def setup_task(self, data):
		pass

	def is_complex(self):
		return True

	# Call this method from each subclass
	def tick(self, elapsed_time_ms):
		self.elapsed += elapsed_time_ms

		# returning False indicates that the tick() function should NOT be called again
		return False

	# Override to do UI stuff!
	def render(self, w, h):
		pass

class p300_clear_tags_task(p300_task):
	def __init__(self):
		p300_task.__init__(self, TASK_CLEAR_TAGS)
		self.db = None

	def perform_task(self, data):
		self.db = data[0]
		self.db.clear_all_tags()

	def get_result(self):
		return True

class p300_scroll_left_task(p300_task):
	def __init__(self):
		p300_task.__init__(self, TASK_SCROLL_LEFT)

	def perform_task(self, data):
		self.new_index = 0
		# data contains: (current index, number of dirs + images in current dir, number of spaces in the matrix)
		(current_index, num_objects, num_spaces) = data
		# check if it's possible to scroll left
		if current_index == 0:
			return

		# move the index by num_spaces
		self.new_index = current_index - num_spaces

	def get_result(self):
		return (self.new_index, )

class p300_scroll_right_task(p300_task):
	def __init__(self):
		p300_task.__init__(self, TASK_SCROLL_RIGHT)

	def perform_task(self, data):
		# data contains: (current index, number of dirs + images in current dir, number of spaces in the matrix)
		(current_index, num_objects, num_spaces) = data
		self.new_index = current_index
		# check if it's possible to scroll right
		if (num_objects - current_index) <= num_spaces:
			return current_index

		self.new_index = current_index + num_spaces

	def get_result(self):
		return (self.new_index, )

class p300_display_selection_task(p300_complex_task):
	def __init__(self):
		p300_complex_task.__init__(self, TASK_DISPLAY_SELECTION)
		self.photo = None
		self.completed = False
		
	def setup_task(self, data):
		self.photo = data

	def tick(self, elapsed_time):
		p300_complex_task.tick(self, elapsed_time)

		if self.elapsed >= PHOTO_DISPLAY_TIME:
			return False

		return True

	def render(self, w, h):
		scale_level = 0.1

		glEnable(GL_TEXTURE_2D)
		glColor4f(1, 1, 1, 1)
		
		glPushMatrix()
		self.photo.load_thumbnail()

		img = self.photo.thumb
		aspect = img.h / float(img.w)

		# scale the image up to fill the screen as much as possible
		ws = w / img.w
		hs = h / img.h

		if ws < hs:
			scale = ws
		else:
			scale = hs
		
		nw = scale * img.w
		nh = scale * img.h

		glTranslatef( w/2, h/2, 0)
		glScalef(nw, nh, 1)		

		glCallList(img.sprite)
		glPopMatrix()

		# if the object is a directory, draw the directory name
		#if isinstance(self.photo, p300_directory_item):
		#	begin_2d_mode(w, h)
		#	glPushMatrix()	
		#	glPopMatrix()
		#	end_2d_mode()

class p300_slideshow_task(p300_complex_task):
	def __init__(self):
		p300_complex_task.__init__(self, TASK_SLIDESHOW)
		self.photolist = None
		self.completed = False
		self.index = 0

	def setup_task(self, data):
		self.photolist = data

	def tick(self, elapsed_time):
		p300_complex_task.tick(self, elapsed_time)

		if self.index >= len(self.photolist):
			# completed slideshow
			return False

		if self.elapsed >= PHOTO_DISPLAY_TIME:
			print 'Slideshow %d/%d'%(self.index+1, len(self.photolist))
			self.index += 1
			self.elapsed = 0

		return True

	def render(self, w, h):
		if self.index >= len(self.photolist): return
		scale_level = 0.1

		glEnable(GL_TEXTURE_2D)
		#glTranslatef(0, 0, 0)	
		glColor4f(1, 1, 1, 1)
		
		glPushMatrix()
		if self.photolist[self.index].thumb == None:
			self.photolist[self.index].thumb = p300_thumbnailer.get_thumbnail_as_glsprite(self.photolist[self.index])

		img = self.photolist[self.index].thumb
		aspect = img.h / float(img.w)

		# scale the image up to fill the screen as much as possible
		ws = w / img.w
		hs = h / img.h

		if ws < hs:
			scale = ws
		else:
			scale = hs
		
		nw = scale * img.w
		nh = scale * img.h

		glTranslatef( w/2, h/2, 0)
		glScalef(nw, nh, 1)		

		glCallList(img.sprite)
		glPopMatrix()

class p300_copy_tagged_task(p300_complex_task):
	def __init__(self):
		p300_complex_task.__init__(self, TASK_COPY_TAGGED)
		self.photolist = None
		self.completed = False
		self.index = 0
		self.curimg = None

	def setup_task(self, data):
		self.photolist = data

	def tick(self, elapsed_time):
		p300_complex_task.tick(self, elapsed_time)

		if self.index >= len(self.photolist):
			# completed task
			return False

		# copy next image
		srcfilename = self.photolist[self.index].filename
		dstfilename = os.path.join(PERSONAL_DIRECTORY, os.path.split(srcfilename)[1])
		print 'Copying image %d: %s -> %s' % (self.index + 1, srcfilename, dstfilename)
		copyfile(srcfilename, dstfilename)
		self.curimg = self.photolist[self.index]
		self.index += 1

		return True

	def render(self, w, h):
		if not self.curimg: return
		
		# draw the thumbnail of the image being copied
		glPushMatrix()
		glEnable(GL_TEXTURE_2D)
		glColor4f(1, 1, 1, 1)
		
		glPushMatrix()
		if self.curimg.thumb == None:
			self.curimg.thumb = p300_thumbnailer.get_thumbnail_as_glsprite(self.curimg)

		img = self.curimg.thumb
		glTranslatef( w/2, h/2, 0)
		glScalef(img.w, img.h, 1)
		glCallList(img.sprite)
		glPopMatrix()

		# draw simple progress bar
		glPushMatrix()
		pbx = WINDOW_BORDER_SIZE_PIXELS
		pby = 0.2 * h
		pbw = (w - (2 * WINDOW_BORDER_SIZE_PIXELS)) / float(len(self.photolist))
		pbh = 40
		pbo = 6

		glDisable(GL_TEXTURE_2D)
		glColor4f(1, 1, 1, 1)

		glRectf(pbx, pby, pbx+(len(self.photolist) * pbw), pby+pbh)
		glColor4f(0.5, 0.5, 0.5, 1)
		glRectf(pbx+pbo, pby+pbo, pbx+(self.index * pbw)-pbo, pby+pbh-pbo)
		glPopMatrix()

		# artificial delay to allow the user to see what's happening
		sleep(IMAGE_COPY_DELETE_DELAY / 1000.0)

class p300_delete_tagged_task(p300_complex_task):
	def __init__(self):
		p300_complex_task.__init__(self, TASK_DELETE_TAGGED)
		self.photolist = None
		self.completed = False
		self.index = 0
		self.curimg = None

	def setup_task(self, data):
		self.photolist = data

	def requires_confirmation(self):
		return True

	def tick(self, elapsed_time):
		p300_complex_task.tick(self, elapsed_time)

		if self.index >= len(self.photolist):
			# completed task
			return False

		# copy next image
		srcfilename = self.photolist[self.index].filename
		deletedir = os.path.join(get_feedback_directory(), ".deleted")
		dstfilename = os.path.join(deletedir, os.path.split(srcfilename)[1])
		if not os.path.exists(deletedir):
			os.mkdir(deletedir)

		print 'Deleting image %d: %s' % (self.index + 1, srcfilename)
		copyfile(srcfilename, dstfilename)
		os.unlink(srcfilename)
		self.curimg = self.photolist[self.index]
		self.index += 1

		return True

	def render(self, w, h):
		if not self.curimg: return

		# draw the thumbnail of the image being copied
		glPushMatrix()
		glEnable(GL_TEXTURE_2D)
		glColor4f(1, 1, 1, 1)
		
		glPushMatrix()
		if self.curimg.thumb == None:
			self.curimg.thumb = p300_thumbnailer.get_thumbnail_as_glsprite(self.curimg)

		img = self.curimg.thumb
		glTranslatef( w/2, h/2, 0)
		glScalef(img.w, img.h, 1)
		glCallList(img.sprite)
		glPopMatrix()

		# draw simple progress bar
		glPushMatrix()
		pbx = WINDOW_BORDER_SIZE_PIXELS
		pby = 0.2 * h
		pbw = (w - (2 * WINDOW_BORDER_SIZE_PIXELS)) / float(len(self.photolist))
		pbh = 40
		pbo = 6

		glDisable(GL_TEXTURE_2D)
		glColor4f(1, 1, 1, 1)

		glRectf(pbx, pby, pbx+(len(self.photolist) * pbw), pby+pbh)
		glColor4f(0.5, 0.5, 0.5, 1)
		glRectf(pbx+pbo, pby+pbo, pbx+(self.index * pbw)-pbo, pby+pbh-pbo)
		glPopMatrix()

		# artificial delay to allow the user to see what's happening
		sleep(IMAGE_COPY_DELETE_DELAY / 1000.0)
