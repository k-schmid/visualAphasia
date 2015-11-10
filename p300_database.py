import sqlite3, os, string
#
# 	A simple wrapper class for an SQLite database containing photo information
#

from p300_items import *
from p300_utility import *

SQL_CREATE_PHOTOS_TABLE = "CREATE TABLE Photos (PhotoID INTEGER PRIMARY KEY, Directory TEXT, Filename TEXT, TagStatus INTEGER)"

class p300_database:
	def __init__(self):
		self.db = None

	def open(self, filename=os.path.join(get_feedback_directory(), 'p300_database.sqlite')):
		if not os.path.exists(filename) and not self.__create_empty_db(filename):
			print '[ERROR] p300_database: failed to open/create database'
			return False

		self.db = sqlite3.connect(filename, isolation_level=None, check_same_thread = False)
		return True

	def __create_empty_db(self, filename):
		self.db = sqlite3.connect(filename)
		c = self.db.cursor()

		c.execute(SQL_CREATE_PHOTOS_TABLE)
		self.db.close()
		return True

	def close(self):
		if self.db:
			self.db.compact()
			self.db.close()
			self.db = None
		
	def compact(self):
		if self.db:
			self.db.execute('VACUUM')

	def get_photo_by_id(self, photoid):
		if not self.db:
			return None

		c = self.db.cursor()
		c.execute('SELECT * FROM Photos WHERE PhotoID = ?', (photoid, ))
		for row in c:
			id = row[0]
			filename = os.path.join(row[1], row[2])
			tagstatus = row[3]
			break
		c.close()
		return p300_photo_item(id, filename, tagstatus)

	def get_items_by_directory(self, directory):
		if not self.db:
			return []

		photos = []
		c = self.db.cursor()
		c.execute('SELECT * FROM Photos WHERE Directory = ?', (directory, ))
		for row in c:
			id = row[0]
			filename = os.path.join(row[1], row[2])
			tagstatus = row[3]
			p = p300_photo_item(id, filename, tagstatus)
			photos.append(p)
		c.close()

		directories = []
		for f in os.listdir(directory):
			if os.path.isdir(os.path.join(directory, f)) and f not in EXCLUDED_DIRECTORIES:
				directories.append(p300_directory_item(TASK_OPEN_DIRECTORY, f))

		return (photos, directories)

	def get_photos_by_directory(self, directory, want_dirs_too=True, recurse=False):
		if not self.db:
			return []

		photos = []
		c = self.db.cursor()
		if recurse:
			c.execute('SELECT * FROM Photos WHERE Directory LIKE ?', (directory,) )
		else:
			c.execute('SELECT * FROM Photos WHERE Directory = ?', (directory, ))
		for row in c:
			id = row[0]
			filename = os.path.join(row[1], row[2])
			tagstatus = row[3]
			p = p300_photo_item(id, filename, tagstatus)
			photos.append(p)
		c.close()

		if want_dirs_too:
			dirs = []
			for f in os.listdir(directory):
				if os.path.isdir(os.path.join(directory, f)) and f not in EXCLUDED_DIRECTORIES:
					dirs.append(p300_folder(f))
			photos = dirs + photos

		return photos

	def get_subdirectories(self, dir):
		if not self.db:
			return []

		dirs = []
		c = self.db.cursor()
		c.execute('SELECT DISTINCT(Directory) FROM Photos WHERE Directory LIKE ?', (dir+"%", ))
		print 'GetSubDir', dir
		for row in c:
			print 'get_subdir:', row[0]
			# check if this directory is a direct child of the parent dir
			split = row[0].replace(dir, "").split(os.sep)
			print split
			if len(split) == 2:
				# means we just have /dirname
				dirs.append(p300_folder(split[1]))
		c.close()

		print dirs

		return dirs

	def get_directories(self):
		if not self.db:
			return []

		dirs = []
		c = self.db.cursor()
		c.execute('SELECT DISTINCT(Directory) FROM Photos')
		for row in c:
			dirname = row[0]
			dirs.append(p300_folder(dirname))
		c.close()
		return dirs

	def get_photos(self):
		if not self.db:
			return []

		photos = []
		c = self.db.cursor()
		c.execute('SELECT * FROM Photos')
		for row in c:
			id = row[0]
			filename = os.path.join(row[1], row[2])
			tagstatus = row[3]
			p = p300_photo_item(id, filename, tagstatus)
			photos.append(p)
		c.close()
		return photos

	def get_tagged_photos(self):
		if not self.db:
			return []

		photos = []
		c = self.db.cursor()
		c.execute('SELECT * FROM Photos WHERE TagStatus = ?', (P300_PHOTO_TAGGED, ))
		for row in c:
			id = row[0]
			filename = os.path.join(row[1], row[2])
			tagstatus = row[3]
			p = p300_photo_item(id, filename, tagstatus)
			photos.append(p)
		c.close()
		return photos

	def clear_all_tags(self):
		if not self.db:
			return False

		c = self.db.cursor()
		c.execute('UPDATE Photos SET TagStatus = ?', (P300_PHOTO_UNTAGGED, ))
		c.close()

		return True

	def set_photo_tagged(self, id):
		return self.__update_photo_status(id, P300_PHOTO_TAGGED)

	def set_photo_untagged(self, id):
		return self.__update_photo_status(id, P300_PHOTO_UNTAGGED)

	def __update_photo_status(self, id, newtagstatus):
		if not self.db:
			return False

		self.db.execute('UPDATE Photos SET TagStatus = ? WHERE PhotoID = ?', (newtagstatus, id))
		return True

	def insert_photo_batch(self, photolist):
		if not self.db:
			return False

		self.db.execute('BEGIN TRANSACTION')
		for p in photolist:
			(path, filename) = os.path.split(p)
			self.db.execute('INSERT INTO Photos VALUES (NULL, ?, ?, ?)', (path, filename, P300_PHOTO_UNTAGGED))
		self.db.execute('COMMIT TRANSACTION')
		return len(photolist)

	def remove_photo_batch(self, photolist):
		if not self.db:
			return False

		self.db.execute('BEGIN TRANSACTION')
		for p in photolist:
			self.db.execute('DELETE FROM Photos WHERE PhotoID = ?', (p.ID,))
		self.db.execute('COMMIT TRANSACTION')
		return True

	def remove_tagged_photos(self):
		if not self.db:
			return False

		self.db.execute('DELETE FROM Photos WHERE TagStatus = ?', (P300_PHOTO_TAGGED, ))
		return True

	def update_database(self, photolist):
		if not self.db:
			return False

		# get all the photos currently in the database
		current_photos = self.get_photos()

		# find those that no longer appear in the database and remove them
		not_found = []
		for p in current_photos:
			if p.filename not in photolist:
				not_found.append(p)
			else:
				photolist.remove(p.filename)
		self.remove_photo_batch(not_found)

		# now add the new photos
		self.insert_photo_batch(photolist)

		return (len(photolist), len(not_found))

	def clear_database(self):
		if not self.db:
			return False

		self.db.execute('DELETE FROM Photos')
		return True
