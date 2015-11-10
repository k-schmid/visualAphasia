import pygame
from pygame.locals import *

import time, math, os, numpy, random, sys

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
from glutils import *

from p300_utility import *
from p300_config import *
from p300_items import *
from p300_thumbnailer import *

class p300_renderer:
	ROWS = 6
	COLS = 6
	
	def __init__(self, base_directory, window_topleft_x_px, window_topleft_y_px, window_width_px, window_height_px, action_handler=None, enable_mouse=True, preserve_aspect_ratios=True, desired_fps=60):
		self.window_pos = (window_topleft_x_px, window_topleft_y_px)
		self.width = window_width_px
		self.height = window_height_px

		# rendering parameters
 		self.flash_level = 0.4
		self.rotate_level = 10
		self.scale_level = 0.1
		self.border_size = 1.0

		self.fps = desired_fps

		self.stimulation_time = 0.2
		self.last_stimulation_time = time.clock()
		self.stimulation_cycle_time = 0.1

		self.handler = action_handler
	
		# manually selected image index
		self.target_image = -1

		self.stimstate = numpy.zeros((p300_renderer.COLS, p300_renderer.ROWS))
		self.images = None

		self.mouse_enabled = enable_mouse

		self.__pygame_init()
		self.__load_gfx(base_directory)
		self.__layout(preserve_aspect_ratios)

	def __pygame_init(self):
		pygame.init()
		os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (self.window_pos[0], self.window_pos[1])
		fontpath = os.path.join(get_feedback_directory(), "fonts")
		fontpath = os.path.join(fontpath, TEXT_FONT)
		fontpath = os.path.normpath(fontpath)
		self.small_font = pygame.font.Font(fontpath, TEXT_SMALL_FONT_SIZE)
		self.default_font = pygame.font.Font(fontpath, TEXT_LARGE_FONT_SIZE)
		self.status_font = pygame.font.Font(fontpath, TEXT_STATUS_FONT_SIZE)
		self.screen = pygame.display.set_mode((self.width, self.height), pygame.OPENGL|pygame.DOUBLEBUF)
		
		glClearColor(0, 0, 0, 1.0)
		glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		glOrtho(0, self.width, 0, self.height, -1, 500)
		glMatrixMode(GL_MODELVIEW)

		glEnable(GL_TEXTURE_2D)
		glEnable(GL_BLEND)
		glEnable(GL_LINE_SMOOTH)

		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		self.glfont = GLFont(self.default_font, (255, 255, 255))
		self.smallglfont = GLFont(self.small_font, (255, 255, 255))
		self.statusglfont = GLFont(self.status_font, (255, 255, 255))

		self.clock = pygame.time.Clock()

		self.__layout(True)

	def close(self):
		pygame.quit()

	# returns the maximum number of images that can be displayed (this value will be different
	# depending on whether the "action bar" is enabled or not)
	def max_images(self):
		return (p300_renderer.ROWS * p300_renderer.COLS)

	def tick(self):
		return self.clock.tick(self.fps)

	def keyup(self, event):
		# handle any key shortcuts here...
		if event.key == K_h:
			self.set_target_image(random.randint(0, 35))
		elif event.key == K_t:
			tagindex = random.randint(0, self.max_images()-1)
			if not self.images[tagindex].is_folder(): self.images[tagindex].tag()
		elif event.key == K_c:
			self.set_target_image(-1)

	def mouseup(self, event):
		print "Mouse clicked at", event.pos
		(x, y) = event.pos
		x = float(x) - self.offset_px - self.x_offset + (self.photo_size / 2.0)
		x = x / (self.photo_size * self.image_spacing_scale)
		y = float(y) - self.offset_px - self.y_offset + (self.photo_size / 2.0)
		y = y / (self.photo_size * self.image_spacing_scale)

		x = int(x)
		y = int(y)
		print x, y, (y*p300_renderer.COLS)+x
		tindex = (y*p300_renderer.COLS)+x

		if self.mouse_enabled:
			self.target_image = tindex

	def handle_events(self):
		quit = False
		for event in pygame.event.get():
			if event.type == KEYDOWN:
				if event.key == K_ESCAPE:
					quit = True
			if event.type == KEYUP:
				self.keyup(event)
			if event.type == MOUSEBUTTONUP:
				self.mouseup(event)
			if event.type == QUIT:
				quit = True
		return quit

	# loads the images used in the graphical effects
	def __load_gfx(self, base_directory):
		self.mask_sprite = GLSprite(os.path.join(base_directory, "gfx/mask.png"), real_size=False)
		self.frame_sprite = GLSprite(os.path.join(base_directory, "gfx/frame.png"), real_size=False)
		self.frame2_sprite = GLSprite(os.path.join(base_directory, "gfx/frame_button.png"), real_size=False)
		self.tick_sprite = GLSprite(os.path.join(base_directory, "gfx/tick-icon.png"), real_size=False)
		self.folder_sprite = GLSprite(os.path.join(base_directory, "gfx/folder.png"), real_size=False)

	# sets up the layout of the OpenGL window 
	def __layout(self, preserve_aspect_ratios):
		self.image_spacing_scale = 1.2 		# image spacing scale (used to space out images in rows and columns)
		self.offset_px = WINDOW_BORDER_SIZE_PIXELS					# space in pixels to leave around the edges of the screen

		# scaling: find out which of the two screen dimensions is going to constrain the size most, and scale
		# the photos to be as big as possible while still staying within those constraints
		required_vertical_space = THUMBNAIL_SIZE_PX * p300_renderer.ROWS * self.image_spacing_scale
		required_horizontal_space = (THUMBNAIL_SIZE_PX * THUMBNAIL_ASPECT_RATIO_LIMIT) * p300_renderer.COLS * self.image_spacing_scale
		available_vertical_space = self.height - (2 * self.offset_px)
		available_horizontal_space = self.width - (2 * self.offset_px)

		print '> Required vertical space is %d pixels (available: %d, diff: %d)' % (required_vertical_space, available_vertical_space, abs(available_vertical_space - required_vertical_space))
		print '> Required horizontal space is %d pixels (available: %d, diff: %d)' % (required_horizontal_space, available_horizontal_space, abs(available_horizontal_space - required_horizontal_space))

		if available_vertical_space < available_horizontal_space:
			# more width than height available, scale to fit height
			self.photo_size = float(available_vertical_space / self.image_spacing_scale) / (p300_renderer.ROWS)
			print '> Scaling images to fit HEIGHT, photo_size = %.2f' % (self.photo_size)

			# and now make sure the images are centred horizontally
			self.x_offset = (available_horizontal_space - (p300_renderer.COLS * self.photo_size)) / 2.0
			self.y_offset = (available_vertical_space - (p300_renderer.ROWS * self.photo_size)) / 2.0
		else:
			# more height than width available, scale to fit width
			self.photo_size = float(available_horizontal_space / self.image_spacing_scale) / (p300_renderer.COLS)
			print '> Scaling images to fit WIDTH, photo_size = %.2f' % (self.photo_size)

			# and now make sure the images are centred vertically
			self.x_offset = (available_horizontal_space - (p300_renderer.COLS * self.photo_size)) / 2.0
			self.y_offset = (available_vertical_space - (p300_renderer.ROWS * self.photo_size)) / 2.0

		print '> x offset: %d, y offset: %d' % (self.x_offset, self.y_offset)

		self.image_coords = {} # maps image indexes (0 .. n) to (x, y) positions
		x = 0
		y = 0
		for i in range(p300_renderer.ROWS * p300_renderer.COLS):		
			self.image_coords[i] = (x, y)
			x = x + 1
			if x>=p300_renderer.COLS:
				x = 0
				y = y + 1

	# loads a new set of images into the renderer. image_set should be list of p300_item objects
	def load_image_set(self, image_set):
		if len(image_set) > self.max_images():
			# should never happen!
			print "[ERROR] too many images passed to load_image_set(), (max %d, got %d)!!!" % (self.max_images(), len(image_set))
			sys.exit(0)

		self.images = {}
		i = 0
		for img in image_set:
			self.images[i] = img
			i += 1

	def draw_centred_text(self, text):
		begin_2d_mode(self.width, self.height)
		size = self.smallglfont.get_size(text)
		position = ((self.width-size[0])/2, (self.height-size[1])/2)
		glPushMatrix()
		glTranslatef(position[0], position[1], 0)
		glColor4f(*FULLSCREEN_TEXT_COLOUR)
		self.glfont.render(text)
		glPopMatrix()
		end_2d_mode()

	def prerender(self):
		glMatrixMode(GL_MODELVIEW)
		glLoadIdentity()
		glClearColor(0,0,0,0)
		glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)

	def render(self, rotate_on=True, flash_on=True, scale_on=True, mask_on=True, empty_frames=True):
		self.__render(rotate_on, flash_on, scale_on, mask_on, empty_frames)

	def postrender(self):
		pygame.display.flip()

	# normal rendering function for the image matrix mode
	def __render(self, rotate_on=True, flash_on=True, scale_on=True, mask_on=True, empty_frames=True):
		self.prerender()

		dt = 1.0 - ((time.clock() - self.last_stimulation_time) / (self.stimulation_time))
		if dt < 0.0:
			dt = 0.0

		simulation_v = self.stimstate * dt

		# ???
		if rotate_on and scale_on and flash_on:
			flash = self.flash_level
		else:
			flash = self.flash_level * 2

		jump = 0.0 # ???
		rotate_rate = 0
		rotate = self.rotate_level * math.cos(time.clock() * rotate_rate)

		# bail out if no images loaded
		if not self.images:
			pygame.display.flip()
			return
					
		glEnable(GL_TEXTURE_2D)

		# TODO
		# draw the status bar thingy
		#begin_2d_mode(self.width, self.height)
		#glPushMatrix()
		#(tw, th) = self.statusglfont.get_size(ROOT_DIRECTORY)
		#glTranslatef((self.width - tw)/2, self.height - self.offset_px - th, 0)
		#glColor4f(*FOLDER_TEXT_COLOUR)
		#self.statusglfont.render(ROOT_DIRECTORY)
		#glPopMatrix()
		#end_2d_mode()

		# translate to bottom left corner of screen
		glTranslatef(0, 0, 0)

		for index in self.image_coords.keys():
			(xc, yc) = self.image_coords[index]
			photo_state = simulation_v[xc][yc]

			# calculate the screen position of this image
			x = (self.offset_px + self.x_offset) + (self.photo_size * self.image_spacing_scale * xc)
			y = (self.offset_px + self.y_offset) + (self.photo_size * self.image_spacing_scale * (p300_renderer.ROWS - yc - 1))

			# retrieve thumbnail (if none, it's an empty slot in the matrix)
			thumb = None
			if self.images[index] != None:
				self.images[index].load_thumbnail()
				thumb = self.images[index].thumb

			glPushMatrix() # first call to glPushMatrix!

			# translate to the top left corner of the image
			glTranslatef(x, y, 0)
			glScalef(self.photo_size*self.border_size*(1+photo_state*self.scale_level), self.photo_size*self.border_size*(1+photo_state*self.scale_level), 1)

			# set up the transformation (use the frame aspect ratio if no thumbnail)
			if thumb: 	aspect = thumb.h/float(thumb.w)
			else: 		aspect = self.frame_sprite.h/float(self.frame_sprite.w)

			glPushMatrix()
			glScalef(1, aspect, 1)
			if rotate_on: glRotatef(photo_state * rotate, 0, 0, 1)
			glTranslatef(0, jump * photo_state, 0)

			# draw the thumbnail
			glColor4f(1, 1, 1, 1)
			if thumb:
				glPushMatrix()
				glCallList(thumb.sprite)
				glPopMatrix()
			
			glDisable(GL_TEXTURE_2D)
			glBlendFunc(GL_SRC_ALPHA, GL_ONE)

			if flash_on: 		glColor4f(1, 1, 1, photo_state*flash)
			else: 				glColor4f(1, 1, 1, 0)

			# draw the flash as a textured quad
			glBegin(GL_QUADS)
			glVertex3f(-0.5, -0.5, 0)
			glVertex3f(0.5, -0.5, 0)
			glVertex3f(0.5, 0.5, 0)
			glVertex3f(-0.5, 0.5, 0)
			glEnd()

			glColor4f(1, 1, 1, 1)
			# draw the highlight box around the target image (if any)
			if self.target_image != -1 and self.target_image == index:
				#glColor4f(0.2, 0.5, 0.2, 0.4)
				glColor4f(*TARGET_IMAGE_COLOUR)
				glBegin(GL_QUADS)
				glVertex3f(-0.7, -0.7, 0)
				glVertex3f(0.7, -0.7, 0)
				glVertex3f(0.7, 0.7, 0)
				glVertex3f(-0.7, 0.7, 0)
				glEnd()

			glEnable(GL_TEXTURE_2D)
			glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

			glColor4f(1, 1, 1, 1)

			# draw the frame 
			if SHOW_ACTIONS_BAR and index < (self.max_images() - ACTION_BAR_SIZE):
				# don't show frame if no thumbnail and empty_frames = False
				if thumb or empty_frames:
					glPushMatrix()
					glCallList(self.frame_sprite.sprite)
					glPopMatrix()
			elif SHOW_ACTIONS_BAR:
				glPushMatrix()
				glCallList(self.frame2_sprite.sprite)
				glPopMatrix()


			# draw a gray overlay on any actions that need confirmed before they can be executed
			if self.images[index] != None and isinstance(self.images[index], p300_action_item) and self.images[index].requires_confirmation():
				if self.images[index].selected_count() < 1:
					glDisable(GL_TEXTURE_2D)
					glColor4f(0.5, 0.5, 0.5, 0.9)
					glBegin(GL_QUADS)
					glVertex3f(-0.5, -0.5, 0)
					glVertex3f(0.5, -0.5, 0)
					glVertex3f(0.5, 0.5, 0)
					glVertex3f(-0.5, 0.5, 0)
					glEnd()
					glEnable(GL_TEXTURE_2D)

			# draw the mask (only if being flashed!)
			if mask_on and photo_state:
				glColor4f(1,1,1,1)
				glPushMatrix()
				glCallList(self.mask_sprite.sprite)
				glPopMatrix()

			glPopMatrix()

			# if the image is currently tagged, draw the tick mark on it
			if self.images[index] != None and isinstance(self.images[index], p300_photo_item) and self.images[index].is_tagged():
				glColor4f(1, 1, 1, 1)
				glPushMatrix()
				glTranslatef(0.35, -0.4, 0)
				glScalef(0.4, 0.4, 1)
				glCallList(self.tick_sprite.sprite)
				glPopMatrix()

			glPopMatrix()

			# if the item represents a folder, draw the first part of the name over it
			if self.images[index] and isinstance(self.images[index], p300_directory_item):
				begin_2d_mode(self.width, self.height)
				glPushMatrix()
				n = self.images[index].dirname
				glTranslatef(x - (self.photo_size * self.image_spacing_scale)/4, y, 0)
				glColor4f(*FOLDER_TEXT_COLOUR)
				
				self.smallglfont.render(n[:FOLDER_TEXT_LIMIT])
				glPopMatrix()
				end_2d_mode()

		self.postrender()

	def set_target_image(self, index):
		self.target_image = index

	# this function should be called on every tick just before render()
	# state should be a list of image indexes from 0 - p300_renderer.ROWS * p300_renderer.COLS
	# that should be stimulated
	def update(self, state=None):
		if state != None:
			self.stimstate = numpy.zeros((p300_renderer.COLS, p300_renderer.ROWS))
			for i in range(len(state)):
				x, y = state[i] % p300_renderer.COLS, (state[i] / p300_renderer.COLS)
				self.stimstate[x][y] = 1
			dt = time.clock() - self.last_stimulation_time
			if dt > self.stimulation_cycle_time:
				self.last_stimulation_time = time.clock()

