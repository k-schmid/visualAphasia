#
# 	Global settings for the photobrowser
#

import os
from p300_tasks import *
from p300_utility import *

# Directory that will be searched (recursively) for photos
# NOTE: use an absolute path!
# TODO warn if not valid
ROOT_DIRECTORY = os.path.normpath(os.path.join(get_feedback_directory(), 'photos'))

# "Personal' directory for the current user
# NOTE: use an absolute path!
# TODO warn if not valid
PERSONAL_DIRECTORY = os.path.normpath('personal directory')

# The size in pixels of the thumbnail images to be generated (this is the height only, image widths
# 	are allowed to vary to a size of THUMBNAIL_SIZE_PX * THUMBNAIL_ASPECT_RATIO_LIMIT. For example 
# 	the default settings of 128 and 1.85 respectively allow a maximum thumbnail width of:
# 		128 * 1.85 = 237 pixels
THUMBNAIL_SIZE_PX = 256

# The maximum allowed aspect ratio (width divided by height) of thumbnail images. Images with an 
# 	aspect ratio less than or equal to this value will be rescaled normally. Images with an aspect
# 	ratio higher than this value will be appear distorted (ie they will be displayed as horizontally
# 	"squashed")
THUMBNAIL_ASPECT_RATIO_LIMIT = 1.85

# Parallel port markers. The marker values can be freely modified as long as you don't change the names
PARALLEL_MARKERS = \
		{\
	"StartExperiment" : 251,\
	"EndExperiment" : 254,\
	"CountdownStart" : 70,\
	"StartBlock" : 0,\
	"EndBlock" : 81,\
	"StartTrial" : 1,\
	"EndTrial" : 2,\
	"TargetMarkerStart" : 120,\
	"MarkerStart" : 20,\
		}

# This variable sets the minimum time (in milliseconds!) that the feedback will allow between 
# sending successive parallel port markers. If you find that some markers are being sent too close
# together you can try increasing this slightly. 
PARALLEL_MARKER_SPACING = 20.0

# This is the text colour that will be used for displaying folder names in the UI
# It is defined in a format OpenGL understands: (red, green, blue, alpha). Each value
# should be in the range 0.0-1.0. The alpha value controls the opacity of the text.
# 0.0 will be fully transparent, 1.0 fully opaque. 
# 	Examples of different colours:
# 		- Red: (1, 0, 0, 1)
# 		- Green: (0, 1, 0, 1)
# 		- Blue: (0, 0, 1, 1)
FOLDER_TEXT_COLOUR = (1, 1, 1, 1)

# This is the text colour that will be used for displaying fullscreen messages like 'Paused' and 'Ende'
# See FOLDER_TEXT_COLOUR for details of the format. 
FULLSCREEN_TEXT_COLOUR = (1, 1, 1, 1)

# This is the target image colour that will be used to highlight images in the UI.
# It is defined in the same format as FOLDER_TEXT_COLOUR, see the description of that
# variable for more information.
TARGET_IMAGE_COLOUR = (0.3, 0.2, 1.0, 0.8)

# This is the maximum number of characters to display in a folder name - the number will
# be limited by the size of the thumbnails, so you might need to adjust this if you change
# the value of THUMBNAIL_SIZE_PX
FOLDER_TEXT_LIMIT = 5

# Set this to True to show the set of action icons in the bottom row of the matrix. Note that
# this limits the number of spaces for images and directories. To remove the set of action icons
# set this option to False
SHOW_ACTIONS_BAR = True

# Number of actions that can be shown on the actions bar. Currently cannot be changed to anything other than 6.
ACTION_BAR_SIZE = 6

# This list defines the buttons that should be shown on the actions bar and the order in which
# they appear on the screen (left to right). Note that while you can switch the buttons around or
# even have multiple copies of the same button, you must have a total of 6 buttons!
# For a description of each ACTION_ value, see p300_actions.py
ACTIONS_BAR_TASKS = [ TASK_SCROLL_LEFT, TASK_CLEAR_TAGS, TASK_COPY_TAGGED, TASK_DELETE_TAGGED, TASK_SLIDESHOW, TASK_SCROLL_RIGHT ]

# Font name to use for drawing text in the UI
TEXT_FONT = 'ProFontWindows.ttf'

# Large font size to use for drawing text in the UI
TEXT_LARGE_FONT_SIZE = 64

# Small font size to use for drawing text in the UI
TEXT_SMALL_FONT_SIZE = 48

# Font size for status bar
TEXT_STATUS_FONT_SIZE = 24

# Time (in milliseconds) to display a photo when it is selected during a slideshow
PHOTO_DISPLAY_TIME = 3000

# Window width in pixels
WINDOW_WIDTH_PIXELS = 1200

# Window height in pixels
WINDOW_HEIGHT_PIXELS = 900

# Text that will be shown on the screen during the inter block pause period
INTER_BLOCK_PAUSE_TEXT = 'Paused'

# Text that will be shown on the screen during the countdown at the end of the inter block pause
# The '%d' substring will be automatically replaced by the number of seconds remaining in the countdown.
# For example, the default text will show '3 seconds...'->'2 seconds...'->'1 seconds...'
INTER_BLOCK_COUNTDOWN_TEXT = '%d seconds...'

# Text that will be shown on the screen when all blocks are completed
EXPERIMENT_COMPLETE_TEXT = 'Ende'

# Size of border around the image grid in pixels
WINDOW_BORDER_SIZE_PIXELS = 10

# The artificial delay (in milliseconds!) inserted after an image is copied or deleted to allow the UI to be updated
IMAGE_COPY_DELETE_DELAY = 500.0

# Directories to skip when searching for images
EXCLUDED_DIRECTORIES = [ '.git', '.svn', '.thumbnails', '.deleted' ]

# Supported image extensions to search for
SUPPORTED_EXTENSIONS = [ '.jpg', '.png', '.bmp' ]
