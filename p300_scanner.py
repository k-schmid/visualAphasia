#
# 	Recursively scans a directory for image files and adds them to an SQLite database
#

import os
from p300_database import p300_database
from p300_config import *


class p300_scanner:
	@staticmethod
	def do_scan(db, toplevel, wipedb=False):
		photos_found = []
		for root, dirs, files in os.walk(toplevel):
			for ed in EXCLUDED_DIRECTORIES:
				if ed in dirs:
					dirs.remove(ed)

			for f in files:
				(fn, ext) = os.path.splitext(f)
				if ext in SUPPORTED_EXTENSIONS:
					photos_found.append(os.path.join(root, f))
		print "[INFO] p300_scanner: found %d photos" % len(photos_found)

		if wipedb:
			# simple case: wipe the database and insert all the newly found photos
			db.clear_database()
			print "[INFO] p300_scanner: inserted %d photos in database" % db.insert_photo_batch(photos_found)
		else:
			# otherwise just attempt to update the existing database (this will add new files that aren't
			# already in the database and delete entries for files that are no longer available)
			(inserted, removed) = db.update_database(photos_found)
			print "[INFO] p300_scanner: photos inserted: %d, photos removed: %d" % (inserted, removed)

		return db.get_photos()
		
