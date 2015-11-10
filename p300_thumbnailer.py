# 	
# 	Class to generate thumbnails for a set of photos
#

import pygame, os
from p300_config import *
from p300_utility import *
from glutils import GLSprite

class p300_thumbnailer:
	@staticmethod
	def generate_thumbnails(photolist, cachefolder=os.path.join(get_feedback_directory(), '.thumbnails')):
		if not os.path.exists(cachefolder):
			os.mkdir(cachefolder)

		for i in range(len(photolist)):
			p = photolist[i]

			thumbname = os.path.join(cachefolder, '[%08d].png' % p.ID)
			# don't regenerate the thumbnail if it is already cached
			if os.path.exists(thumbname):
				continue

			try:
				img = pygame.image.load(p.filename)
			except:
				print "[WARNING] p300_thumbnailer: failed to load '%s'" % p.filename
				continue

			print "Generating thumbnail %d/%d (%s)..." % (i+1, len(photolist), p.filename)

			aspect = float(img.get_width())/img.get_height()
			if aspect > THUMBNAIL_ASPECT_RATIO_LIMIT:
				aspect = THUMBNAIL_ASPECT_RATIO_LIMIT
			thumb = pygame.transform.smoothscale(img, (THUMBNAIL_SIZE_PX*aspect, THUMBNAIL_SIZE_PX))
			(path, filename) = os.path.split(p.filename)
			pygame.image.save(thumb, thumbname)

			del img, thumb

		return True

	@staticmethod
	def get_thumbnail(photo, cachefolder=os.path.join(get_feedback_directory(), '.thumbnails')):
		if not os.path.exists(cachefolder):
			os.mkdir(cachefolder)

		cfilename = os.path.join(cachefolder, '[%08d].png'%(photo.ID))
		if not os.path.exists(cfilename):
			return None
		
		return pygame.image.load(cfilename)

	@staticmethod
	def get_thumbnail_as_glsprite(photo, cachefolder=os.path.join(get_feedback_directory(), '.thumbnails')):
		if not os.path.exists(cachefolder):
			os.mkdir(cachefolder)

		cfilename = os.path.join(cachefolder, '[%08d].png'%(photo.ID))
		if not os.path.exists(cfilename):
			return None

		return GLSprite(cfilename)
