import math, sys, random, time, os
import pygame
from pygame.locals import *
from numpy import *
import glutils

from p300_items import *
from p300_utility import *
from p300_renderer import *
from p300_scanner import *
from p300_thumbnailer import *
from p300_database import *
from p300_config import *
from p300_sequence import *
from p300_decision import *
from p300_scorer import *

if __name__ == "__main__":
	fbdir = get_feedback_directory()
	pyffdir = fbdir[:fbdir.find("src")+3]
	print pyffdir
	sys.path.append(pyffdir)

from FeedbackBase.MainloopFeedback import MainloopFeedback

[
		STATE_INITIAL, 				# starting state, before anything happens
		STATE_STARTING_BLOCK, 		# starting a block
		STATE_STARTING_TRIAL, 		# starting a trial 
		STATE_SUBTRIAL, 			# during a subtrial 
		STATE_BETWEEN_TRIALS, 		# between trials
		STATE_BETWEEN_BLOCKS, 		# between blocks
		STATE_FINISHED, 			# finished all blocks
		STATE_CUSTOM_ACTION, 		# performing a custom action 
] = range(8)

class p300_photobrowser(MainloopFeedback):
	def init(self):
		"""Create the class and initialise variables that must be in place before pre_mainloop is called"""
	
		# 	Variables: window position and size
		self.screen_width = WINDOW_WIDTH_PIXELS 			# window width in pixels
		self.screen_height = WINDOW_HEIGHT_PIXELS 			# window height in pixels
		self.screen_x = 50				# x position of left top corner of the window in pixels
		self.screen_y = 50 				# y position of left top corner of the window in pixels

		# 	Variables: limits/counts
		self.num_blocks = 3
		self.num_trials = 8
		self.num_subtrials_per_iteration = 2
		self.num_iterations = 2

		# 	Variables: durations and pauses (all times in MILLISECONDS)
		self.startup_sleep_duration 				= 2 				# pause on startup to allow the classifier time to initialise. Set to 0 to disable. 
		self.cue_presentation_duration 				= 3500 
		self.pre_cue_pause_duration 				= 2000
		self.post_cue_presentation_pause_duration 	= 2000
		self.inter_trial_duration 					= 3000
		self.stimulus_duration 						= 100
		self.inter_stimulus_duration 				= 200
		self.inter_block_pause_duration 			= 15000
		self.inter_block_countdown_duration 		= 3000
		self.result_presentation_duration 			= 5000

		# 	Variables: miscellaneous
		self.max_inter_score_duration 				= 1000 # maximum time in milliseconds to allow between successive scores being received 

		# 	Variables: switches (all booleans)
		self.rotation_enable = True 					# if True, activates the rotation effect during stimulus presentation
		self.flash_enable = True						# if True, activates the flash effect during stimulus presentation
		self.scaling_enable = True 						# if True, activates the scaling effect during stimulus presentation
		self.mask_enable = True 						# if True, activates the mask overlay during stimulus presentation
		self.udp_markers_enable = True 					# if True, activates the sending of UDP markers when send_parallel is called
		self.online_mode_enable = True 					# if True, activates online mode
		self.row_col_eval_enable = True 				# if True, activates row/column mode in the sequence generator
		self.display_selection_enable = True 			# if True, activates the displaying of the selected object after each trial
		self.show_empty_image_frames_enable = True 		# if True, empty slots in the grid will still contain the standard image frame graphic
		self.mask_sequence_enable = True 				# if True, the sequence module will have a mask passed to it indicating which entries in the grid are full/empty

		####################################################
		# 	Variables: private variables after this line!  #
		####################################################

		self._state = STATE_INITIAL 					# current state of the feedback
		self._exstate = {} 								# extended state information
		self._exstate['CurrentBlock'] = 0 				# number of the current block
		self._exstate['CurrentTrial'] = 0 				# number of the current trial
		self._exstate['CurrentSubtrial'] = 0 			# number of the current subtrial
		self._exstate['TrialElapsed'] = 0 				# elapsed time during the start trial phase
		self._exstate['BlockPauseElapsed'] = 0 			# elapsed time during the inter block pause
		self._exstate['SubtrialElapsed'] = 0 			# elapsed time during the current subtrial
		self._exstate['TrialPauseElapsed'] = 0 			# elapsed time during the inter trial pause
		self._exstate['ScoresReceived'] = 0 			# indicates how many scores have been received for the current trial
		self._exstate['SubtrialMarkersSent'] = 0 		# indicates how many markers have been sent for the current subtrial
		self._exstate['OfflineTargetIndex'] = -1		# indicates the randomly selected target image in offline mode

		self._maxindex = p300_renderer.COLS * p300_renderer.ROWS

		# This variable defines the action(s) that will be taken, if any, at the end of the next trial
		# 	If it is set to [], the feedback will continue on to the next trial immediately.
		# 	If it set to a list of p300_action objects, the feedback will hand control over to that object
		# 	at the end of the trial, and the objects will then be able to perform whatever tasks they
		# 	wants before restoring control to the feedback, which will then continue on with the next
		# 	trial. 
		self._nextactions = []

		# open the image database
		self._db = p300_database()
		self._db.open()

		# current directory
		self._directory = ROOT_DIRECTORY
		
		# generate thumbnails as needed
		p300_thumbnailer.generate_thumbnails(p300_scanner.do_scan(self._db, self._directory))
	
		# stores the time that the last parallel port marker was sent - this is used by safe_send_parallel
		# to ensure that successive markers are sufficiently separated.
		self._last_marker_sent_time = time.clock()

		# this stores the starting position of the current photoset in the list of all the entries in the current directory
		self._photoset_starting_index = 0
	
		# the last object selected
		self._last_selected_index = -1
	
		# mask of the image grid (1 = position filled, 0 = empty)
		self._mask = []

		# object which handles scoring/sequence generator/decisions
		self._scorer = p300_scorer()

		self._TESTING_MODE = True

		self._last_action_id = 0
		self._last_score_received_at = -1
		self._action_bar_items = []

	def construct_actions_bar(self):
		self._action_bar_items = []
		for i in range(ACTION_BAR_SIZE):
			a = p300_action_item(ACTIONS_BAR_TASKS[i])
			a.load_thumbnail()
			self._action_bar_items.append(a)

	def construct_item_set(self):
		# builds the list of items that should be displayed in the UI (ie the set of photos, directories and actions)
		# the process for constructing the list goes like this:
		# 	1. If not in ROOT_DIRECTORY, insert a ".." directory entry as the first item, else go to step 2.
		# 	2. Insert any subdirectories in the current directory, up to a maximum number determined by the use of the action bar and presence of the .. entry
		# 	3. If any spaces remaining, insert photos up to a maximum number determined by the use of the action bar and presence of the directory entries
		# 	4. Insert the action bar covering the last 6 spaces if activated

		# start by retrieving all the directories and photos for the directory we're in
		(photos, directories) = self._db.get_items_by_directory(self._directory)

		# clear the mask
		self._mask = [[0 for j in range(p300_renderer.COLS)] for i in range(p300_renderer.ROWS)]

		print "> Constructing item set"
		itemset = []
		limit = self._renderer.max_images()
		if self._directory != ROOT_DIRECTORY:
			# append the ".." entry
			#print "> Inserting .. entry"
			itemset.append(p300_directory_item(TASK_OPEN_DIRECTORY, ".."))

		if SHOW_ACTIONS_BAR:
			limit -= ACTION_BAR_SIZE

		all_objects = directories + photos

		#print "> Have %d items to fill with directories and images" % limit
		
		objindex = self._photoset_starting_index
		while objindex < len(all_objects) and len(itemset) < limit:
			obj = all_objects[objindex]
			itemset.append(obj)
			#print '> %d : Inserted %s' % (len(itemset), all_objects[objindex])
			objindex += 1

		# insert empty slots if needed
		for i in range(limit - len(itemset)):
			itemset.append(None)
			#print '> %d : Inserted blank entry' % (len(itemset))

		# insert the action bar if turned on
		if SHOW_ACTIONS_BAR:
			itemset += self._action_bar_items

		#print 'Constructed set of %d items' % (len(itemset))

		# populate the mask
		for i in range(len(itemset)):
			if itemset[i]:
				mx = i % p300_renderer.COLS
				my = i / p300_renderer.ROWS
				self._mask[my][mx] = 1

		#for i in range(p300_renderer.ROWS):
		#	print self._mask[i]

		return itemset

	def pre_mainloop(self):
		print '> Creating renderer and loading images'
		# this is the object responsible for displaying the UI
		self._renderer = p300_renderer(get_feedback_directory(), self.screen_x, self.screen_y, self.screen_width, self.screen_height, self, self._TESTING_MODE)
		self.construct_actions_bar()
		# load the initial set of photos from the root directory
		self._photoset_starting_index = 0;
		self._photoset = self.construct_item_set()
		self._renderer.load_image_set(self._photoset)

		time.sleep(self.startup_sleep_duration/1000.0)
		self.safe_send_parallel(PARALLEL_MARKERS["StartExperiment"])
		self._state = STATE_STARTING_BLOCK

	def safe_send_parallel(self, marker):
		#print "%.4f / %.4f" % (time.clock(), self._last_marker_sent_time)
		diff_in_seconds = time.clock() - self._last_marker_sent_time
		diff_in_milliseconds = 1000.0 * diff_in_seconds

		if (diff_in_seconds * 1000.0) < PARALLEL_MARKER_SPACING:
			spacing_required = (PARALLEL_MARKER_SPACING - diff_in_milliseconds) / 1000.0
			#print '> safe_send_parallel inserting a delay of %f seconds!!!' % spacing_required
			#time.sleep(spacing_required)
		self.send_parallel(marker)
		self._last_marker_sent_time = time.clock()

	def post_mainloop(self):
		print "p300_photobrowser: post_mainloop"

	# handles shutdown
	def quit(self):
		self._renderer.close()
		sys.exit(0)

	def tick(self):
		# get the time in milliseconds since this function was last called
		self.elapsed = self._renderer.tick()

		# handle any pygame events
		do_quit = self._renderer.handle_events()
		if do_quit: self.quit()

		if self.elapsed >= 100:
			print '\n\n*** STALL DETECTED (%d ms since last call to tick())\n\n' % self.elapsed
			if self._state == STATE_SUBTRIAL or self._state == STATE_STARTING_TRIAL or self._state == STATE_BETWEEN_TRIALS:
				print '*** Reducing elapsed time from %dms to %dms after stall!' % (self.elapsed, 50)
				self.elapsed = 50

		# update the feedback state
		self.update_state()

		# update the UI
		if self._state != STATE_CUSTOM_ACTION or not self._nextactions[0].is_complex():
			# if in a state where the grid should be displayed, call the standard render() function
			if self._state != STATE_BETWEEN_TRIALS and self._state != STATE_BETWEEN_BLOCKS and self._state != STATE_FINISHED:
				self._renderer.render(self.rotation_enable, self.flash_enable, self.scaling_enable, self.mask_enable, self.show_empty_image_frames_enable)
			else:
				# otherwise draw a blank screen with the appropriate text for the current state
				self._renderer.prerender()
				if self._state == STATE_BETWEEN_BLOCKS:
					if self._exstate['BlockPauseElapsed'] >= self.inter_block_pause_duration - self.inter_block_countdown_duration:
						self._renderer.draw_centred_text(INTER_BLOCK_COUNTDOWN_TEXT % (1 + ((self.inter_block_pause_duration - self._exstate['BlockPauseElapsed'])/1000)))
					else:
						self._renderer.draw_centred_text(INTER_BLOCK_PAUSE_TEXT)

				elif self._state == STATE_FINISHED:
					self._renderer.draw_centred_text(EXPERIMENT_COMPLETE_TEXT)
				self._renderer.postrender()

	def handle_state_start_block(self):
		# just start the first trial in this block
		self.safe_send_parallel(PARALLEL_MARKERS['StartBlock'])
		self._state = STATE_STARTING_TRIAL
		self.preset_state_for_block()
		self.preset_state_for_trial()

	def handle_state_between_blocks(self):
		if not self._exstate.has_key('Block%dFinished'%self._exstate['CurrentBlock']):
			# send block finished marker
			self.safe_send_parallel(PARALLEL_MARKERS['EndBlock'])
			self._exstate['Block%dFinished'%self._exstate['CurrentBlock']] = True
			print '> Block %d FINISHED' % self._exstate['CurrentBlock']

			print '+++ Block %d FINISHED' % self._exstate['CurrentBlock']

		if self._exstate.has_key('Block%dFinished'%(self.num_blocks-1)):
			# finished!
			self._state = STATE_FINISHED

		if self.inter_block_pause_duration - self._exstate['BlockPauseElapsed'] <= self.inter_block_countdown_duration:
			if not self._exstate.has_key('BlockCountdown%d'%self._exstate['CurrentBlock']):
				self.safe_send_parallel(PARALLEL_MARKERS['CountdownStart'])
				self._exstate['BlockCountdown%d'%self._exstate['CurrentBlock']] = True

			# start showing countdown in the UI
			self._renderer.draw_centred_text('%d ms ...'%(self.inter_block_pause_duration - self._exstate['BlockPauseElapsed']))

		if self._exstate['BlockPauseElapsed'] >= self.inter_block_pause_duration:
			# block pause is over, start new block
			self._state = STATE_STARTING_BLOCK
			self._exstate['CurrentBlock'] += 1
			print '> Starting new block'

		self._exstate['BlockPauseElapsed'] += self.elapsed

	def handle_state_start_trial(self):
		if self._exstate['TrialElapsed'] >= self.pre_cue_pause_duration:
			if not self._exstate.has_key('SeqGenerated%d'%self._exstate['CurrentTrial']):

				# reset the scoring object and generate new sequence for this trial
				params = {'num_iter' : self.num_iterations, 'num_subt_per_iter' : self.num_subtrials_per_iteration}
				if self.mask_sequence_enable:
					params['mask'] = self._mask
				self._scorer.reset_on_new_trial(params, params)
				self._exstate['SeqGenerated%d'%self._exstate['CurrentTrial']] = True
				print '> Generated sequence data for %d subtrials' % len(self._scorer.sequencedata())

				# send the start trial marker
				self.safe_send_parallel(PARALLEL_MARKERS['StartTrial'])

				# if in offline mode
				if not self.online_mode_enable:
					# select a random image to highlight
					r = random.randint(0, self._maxindex - 1)
					self._exstate['OfflineTargetIndex'] = r
					self._renderer.set_target_image(self._exstate['OfflineTargetIndex'])
					#self.safe_send_parallel(PARALLEL_MARKERS['TargetMarkerStart'])

		if self._exstate['TrialElapsed'] >= self.pre_cue_pause_duration + self.cue_presentation_duration:
			if not self.online_mode_enable:
				self._renderer.set_target_image(None)

		if self._exstate['TrialElapsed'] >= self.pre_cue_pause_duration + self.cue_presentation_duration + self.post_cue_presentation_pause_duration:
			print '> Starting trial %d' % self._exstate['CurrentTrial']
			self._state = STATE_SUBTRIAL
			self._exstate['SubtrialElapsed'] = 0
			self._exstate['TrialPauseElapsed'] = 0

		self._exstate['TrialElapsed'] += self.elapsed

	def handle_state_between_trials(self):
		if not self._exstate.has_key('TrialFinished%d'%self._exstate['CurrentTrial']):
			self._exstate['TrialFinished%d'%self._exstate['CurrentTrial']] = True
			self.safe_send_parallel(PARALLEL_MARKERS['EndTrial'])
			print '+++ Block %d, Trial %d FINISHED' % (self._exstate['CurrentBlock'], self._exstate['CurrentTrial'])

		if self._exstate['TrialPauseElapsed'] >= self.inter_trial_duration:
			# move on to next trial immediately in offline mode
			# if in online mode, may have to wait for all the scores
			if not self.online_mode_enable or self._TESTING_MODE or (self.online_mode_enable and self._scorer.all_scores_received()):
				self._exstate['CurrentTrial'] += 1

				# this is just for testing purposes, normally this is done in the update_scores() function
				if self.online_mode_enable and self._TESTING_MODE:
					print "> TESTING MODE, selected index set to %d" % (self._renderer.target_image)
					self.setup_custom_action(self._renderer.target_image)

				# once we are ready to move on to the next trial, check if the object selected requires a 
				# custom action to be executed. If so, the state gets changed to STATE_CUSTOM_ACTION and 
				# the action is executed. Otherwise we start the next trial (or the next block if this was the
				# last trial)
				if len(self._nextactions) > 0:
					self._state = STATE_CUSTOM_ACTION
					print "Activating action %d/%d, type" % (1, len(self._nextactions)), type(self._nextactions[0])

					for n in self._nextactions:
						# set the state to enter after the custom action is complete
						if self._exstate['CurrentTrial'] == self.num_trials:
							n.set_next_state(STATE_BETWEEN_BLOCKS)
						else:
							n.set_next_state(STATE_STARTING_TRIAL)

					# new trial coming up (after the actions), reset state
					if self._exstate['CurrentTrial'] != self.num_trials:
						self.preset_state_for_trial()
				else:
					# if all trials completed, go to start of next block
					if self._exstate['CurrentTrial'] == self.num_trials:
						print '> %d trials complete, entering block pause' % self.num_trials
						self._state = STATE_BETWEEN_BLOCKS
					else:
						# otherwise start next trial
						print '> Moving to next trial'
						self.preset_state_for_trial()
						self._state = STATE_STARTING_TRIAL
			# if we're still waiting on scores to come in, check if it's been a long time since the last one...
			elif self.online_mode_enable and not self._scorer.all_scores_received():
				gap = int((time.clock() - self._last_score_received_at) * 1000)
				if self._last_score_received_at != -1:
					print 'Waiting for scores, gap = %dms' % gap
				if self._last_score_received_at != -1 and gap > self.max_inter_score_duration:
					# Display a warning message and rerun the current trial
					print '*****************************************'
					print 'WARNING: Rerunning trial %d due to missing scores (time from last score = %d ms)!' % (self._exstate['CurrentTrial'], gap)
					print '*****************************************'
					self.preset_state_for_trial()
					self._state = STATE_STARTING_TRIAL
			
		self._exstate['TrialPauseElapsed'] += self.elapsed

	def handle_state_subtrial(self):
		first_marker_sent_this_time = False
		if not self._exstate.has_key('MarkerStartSubtrial%d'%(self._exstate['CurrentSubtrial'])):
			if self.online_mode_enable:
				self.safe_send_parallel(PARALLEL_MARKERS['MarkerStart'])
			else:
				current_subtrial = self._exstate['CurrentSubtrial']
				if self._exstate['OfflineTargetIndex'] == -1 or self._exstate['OfflineTargetIndex'] not in self._scorer.sequencedata()[current_subtrial]:
					base_marker = PARALLEL_MARKERS['MarkerStart']
				else:
					base_marker = PARALLEL_MARKERS['TargetMarkerStart']

				self.safe_send_parallel(base_marker)
			#self.safe_send_parallel(PARALLEL_MARKERS['MarkerStart'])
			self._exstate['MarkerStartSubtrial%d'%(self._exstate['CurrentSubtrial'])] = True
			first_marker_sent_this_time = True

		if self._exstate['SubtrialElapsed'] <= self.stimulus_duration:
			# start triggering the stimulus in the UI
			self._renderer.update(self._scorer.sequencedata()[self._exstate['CurrentSubtrial']])
		else:
			self._renderer.update(None)

		# send an image index marker each time through this function
		if not first_marker_sent_this_time and self._scorer.sequencedata():
			current_subtrial = self._exstate['CurrentSubtrial']
			current_marker_index = self._exstate['SubtrialMarkersSent']

			# TEMPORARY CODE
			#if current_marker_index < 1:
			#	current_marker_value = self._scorer.sequencedata()[current_subtrial][current_marker_index]

				

			#	self._exstate['SubtrialMarkersSent'] += 1

			# ORIGINAL CODE (for sending all the markers)
			# check if we still have markers to send
			#if current_marker_index < len(self._scorer.sequencedata()[current_subtrial]):
			#	current_marker_value = self._scorer.sequencedata()[current_subtrial][current_marker_index]
			#	# in online mode, just send the indexes offset from MarkerStart
			#	if self.online_mode_enable:
			#		self.safe_send_parallel(PARALLEL_MARKERS['MarkerStart']+ 1 + current_marker_value)
			#	else:
			#		# in offline mode, do the same except when the image was also the target for the current trial
			#		if self._exstate['OfflineTargetIndex'] == -1 or self._exstate['OfflineTargetIndex'] != current_marker_value:
			#			base_marker = PARALLEL_MARKERS['MarkerStart']
			#		else:
			#			base_marker = PARALLEL_MARKERS['TargetMarkerStart']
			#
			#		self.safe_send_parallel(base_marker + 1 + current_marker_value)
			#	# increment number of markers sent
			#	self._exstate['SubtrialMarkersSent'] += 1

		if self._exstate['SubtrialElapsed'] >= self.stimulus_duration + self.inter_stimulus_duration:
			self._exstate['CurrentSubtrial'] += 1

			print "> Finished subtrial %d/%d)" % (self._exstate['CurrentSubtrial'], len(self._scorer.sequencedata()))
			if self._exstate['CurrentSubtrial'] == len(self._scorer.sequencedata()):
				# finished last subtrial
				print "Moving into between trials state"
				self._state = STATE_BETWEEN_TRIALS
			else:
				# continue to next subtrial
				self.preset_state_for_subtrial()

		self._exstate['SubtrialElapsed'] += self.elapsed

	def handle_state_finished(self):
		if not self._exstate.has_key('Finished'):
			self.safe_send_parallel(PARALLEL_MARKERS['EndExperiment'])
			self._exstate['Finished'] = True

	def preset_state_for_trial(self):
		self._exstate['TrialElapsed'] = 0
		self._exstate['CurrentSubtrial'] = 0
		self._exstate['TrialPauseElapsed'] = 0
		self._exstate['ScoresReceived'] = 0
		self._exstate['OfflineTargetIndex'] = -1
		self._exstate['CurrentSubtrial'] = 0
		for k in self._exstate.keys():
			if k.startswith('MarkerStartSubtrial'):
				del self._exstate[k]

		self._last_score_received_at = -1
		self.preset_state_for_subtrial()

	def preset_state_for_block(self):
		self._exstate['BlockPauseElapsed'] = 0
		self._exstate['CurrentTrial'] = 0
		for k in self._exstate.keys():
			if k.startswith('SeqGenerated') or k.startswith('TrialFinished'):
				del self._exstate[k]

	def preset_state_for_subtrial(self):
		self._exstate['SubtrialMarkersSent'] = 0
		self._exstate['SubtrialElapsed'] = 0

	def handle_state_custom_action(self):
		# action can be "UI" actions (they draw stuff on the screen) or "non-UI" actions (which don't draw anything)
		# if the action isn't a UI action, just call the tick() method...
		if not self._nextactions[0].is_complex():
			self._nextactions[0].tick(self.elapsed)
		else:
			# but if it IS a UI action, call tick(), then the render() method in between calls to the main renderer
			task_ongoing = self._nextactions[0].tick(self.elapsed)
			self._renderer.prerender()
			self._nextactions[0].render(self.screen_width, self.screen_height)

			if self._nextactions[0].ID == TASK_DISPLAY_SELECTION and isinstance(self._nextactions[0].photo, p300_directory_item):
				self._renderer.draw_centred_text(os.path.split(self._directory)[1])

			self._renderer.postrender()
			
		if not task_ongoing:
			print "> Action completed"
			last_action = self._nextactions[0]

			# remove the current action from the list
			self._nextactions = self._nextactions[1:]

			self._last_action_id = last_action.ID
			
			# if no actions left, restore the correct state and contine
			if len(self._nextactions) == 0:
				self._state = last_action.restore_state()
			else:
				# continue to next action...
				print '> Starting next action'

	def update_state(self):
		if self._state == STATE_INITIAL:
			print "> Initial state"
		elif self._state == STATE_STARTING_BLOCK:
			self.handle_state_start_block()
		elif self._state == STATE_STARTING_TRIAL:
			self.handle_state_start_trial()
		elif self._state == STATE_SUBTRIAL:
			self.handle_state_subtrial()
		elif self._state == STATE_BETWEEN_TRIALS:
			self.handle_state_between_trials()
		elif self._state == STATE_BETWEEN_BLOCKS:
			self.handle_state_between_blocks()
		elif self._state == STATE_FINISHED:
			self.handle_state_finished()
		elif self._state == STATE_CUSTOM_ACTION:
			self.handle_state_custom_action()
		else:
			print "*** Unknown state ***"
			self._renderer.close()
			sys.exit(0)

	def update_scores(self, score_data):
		# update the scores
		if self._last_score_received_at == -1:
			print '> *** 1st score received!'
		else:
			print '> *** Score received (time from last score was %.3fs)' % (time.clock() - self._last_score_received_at)
		self._last_score_received_at = time.clock()
		self._scorer.add_set_of_scores(score_data)

		if self._scorer.all_scores_received():
			# calculate the winner!
			winner = self._scorer.query_winner()
			print '> WINNING IMAGE: %d' % (winner)

			self.setup_custom_action(winner)

	def setup_custom_action(self, winning_index):
		# configures an action in response to a selection

		# get the type of the object at this index (it could be a folder, an image or an action)
		obj = self._photoset[winning_index]
		self._nextactions = []
		
		print '> Custom action for object type:', obj

		# check for actions which need confirmation
		if SHOW_ACTIONS_BAR:
			for o in self._action_bar_items:
				if isinstance(o, p300_action_item):
					if o.requires_confirmation() and obj.ID == o.ID:
						o.was_selected()
						print '> Action ID: %d selected' % (o.ID)
					elif o.requires_confirmation():
						print '> Action ID: %d selection count reset' % (o.ID)
						o.reset_count()

		if isinstance(obj, p300_photo_item):
			# photo object: toggle the tagged state on the object and update the DB accordingly
			obj.toggle_tag()
			print '> Toggled tag on image index %d (%s)' % (obj.ID, obj.filename)
			if obj.is_tagged():
				self._db.set_photo_tagged(obj.ID)
			else:
				self._db.set_photo_untagged(obj.ID)

			# add a task to display the image if enabled
			if self.display_selection_enable:
				dt = p300_display_selection_task()
				dt.setup_task(obj)
				self._nextactions.append(dt)

		elif isinstance(obj, p300_directory_item):
			# directory object: change the current directory to the new one and then reload the photoset
			if obj.dirname == "..":
				# chop the last directory off the path
				self._directory = os.path.split(self._directory)[0]
			else:
				# append dirname to the current path
				self._directory = os.path.join(self._directory, obj.dirname)

			print '> Changed directory to: %s' % self._directory

			if self.display_selection_enable:
				dt = p300_display_selection_task()
				dt.setup_task(obj)
				self._nextactions.append(dt)

			# load new set of items
			self._photoset_starting_index = 0;
			self._photoset = self.construct_item_set()
			self._renderer.load_image_set(self._photoset)
		elif isinstance(obj, p300_action_item):
			# action object: do whatever the action requires. Some actions can be executed
			# immediately, others may be longer running and require creating an action object
			# to perform whatever tasks they need to do.

			if self.display_selection_enable:
				dt = p300_display_selection_task()
				dt.setup_task(obj)
				self._nextactions.append(dt)

			# these 3 are all simple tasks that can be executed immediately
			if obj.ID == TASK_SCROLL_LEFT:
				print '> Scrolling left'
				sa = p300_scroll_left_task()
				num_spaces = self._renderer.max_images()
				if SHOW_ACTIONS_BAR: num_spaces -= ACTION_BAR_SIZE
				(photos, directories) = self._db.get_items_by_directory(self._directory)
				sa.perform_task((self._photoset_starting_index, len(photos) + len(directories), num_spaces))
				self._photoset_starting_index = sa.get_result()[0]
				self._photoset = self.construct_item_set()
				self._renderer.load_image_set(self._photoset)
			elif obj.ID == TASK_SCROLL_RIGHT:
				print '> Scrolling right'
				sa = p300_scroll_right_task()
				num_spaces = self._renderer.max_images()
				if SHOW_ACTIONS_BAR: num_spaces -= ACTION_BAR_SIZE
				(photos, directories) = self._db.get_items_by_directory(self._directory)
				sa.perform_task((self._photoset_starting_index, len(photos) + len(directories), num_spaces))
				self._photoset_starting_index = sa.get_result()[0]
				self._photoset = self.construct_item_set()
				self._renderer.load_image_set(self._photoset)
			elif obj.ID == TASK_CLEAR_TAGS:
				print '> Clearing tags'
				ca = p300_clear_tags_task()
				ca.perform_task((self._db, ))
				# reload photoset
				self._photoset = self.construct_item_set()
				self._renderer.load_image_set(self._photoset)

			# these three are potentially longer running or require confirmation
			elif obj.ID == TASK_DELETE_TAGGED:
				print '> Delete tagged images'
				if obj.selected_count() < 2:
					print '> NOT CONFIRMED, need to select it again!'
					return

				da = p300_delete_tagged_task()
				da.setup_task(self._db.get_tagged_photos())
				self._nextactions.append(da)

				obj.reset_count()

				# just delete the images from the db here
				self._db.remove_tagged_photos()
	
				self._photoset_starting_index = 0
				self._photoset = self.construct_item_set()
				self._renderer.load_image_set(self._photoset)
			elif obj.ID == TASK_COPY_TAGGED:
				print '> Copy tagged images'
				ca = p300_copy_tagged_task()
				ca.setup_task(self._db.get_tagged_photos())
				self._nextactions.append(ca)
			elif obj.ID == TASK_SLIDESHOW:
				sa = p300_slideshow_task()
				sa.setup_task(self._db.get_tagged_photos())
				self._nextactions.append(sa)
			else:
				pass

		else:
			# ??? 
			pass

		self._last_selected_index = winning_index

	# called when new data received from pyff
	def on_control_event(self,data):
		if data.has_key(u'cl_output'):
			score_data = data[u'cl_output']
			self.update_scores(score_data)

	# variable was changed through pyff
	def on_interaction_event(self, data):
		# TODO which variables should be able to be changed while the feedback is running?
		pass

if __name__ == "__main__":
	# simulate pyff for rapid testing
	p = p300_photobrowser()
	p.on_init()
	p._on_play()

