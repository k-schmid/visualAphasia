import math, sys, random, time
import pygame
import os
from pygame.locals import *
from numpy import *
import glutils
import logging
logging.basicConfig()
import random
from threading import Thread


from p300browser import *

from FeedbackBase.MainloopFeedback import MainloopFeedback

import load_highlights

P300_START_EXP = 251
P300_END_EXP = 254
P300_COUNTDOWN_START = 70
P300_START_BLOCK = 0
P300_END_BLOCK = 81
P300_START_TRIAL = 1
P300_END_TRIAL = 2
File_Path = os.path.dirname(globals()["__file__"]) + "/highlights.csv"


[
                STATE_STARTING_TRIAL,       # State before stimulation (Showing the images for a while)
                STATE_REPETITION,           # State while stimulation is going on
                STATE_INITIAL,              # State if no visual feedback is given (black screen)
] = range(3)

# This is the main class for the VisualAphasiaStimulator
class VisualAphasiaStimulator(MainloopFeedback):
        def init(self):
                """Create the class and initialise variables that must be in place before
                browser can be started"""

                # Screen Settings
                self.screen_w = 500
                self.screen_h = 300
                self.screenPos = [100, 100]

                # Number of rows and columns in the matrix
                self.row = 2
                self.col = 3
                self.max_photos = self.col * self.row

                self.online_mode = False

                self.trial_count = 2

                # Time the target is presented to the user before stimulation
                self.trial_highlight_duration = 0#3500
                # Time before the target is presented to the user
                self.trial_pre_highlight_duration = 0#2000
                # Pre trial Pause (between Target presentation and trial start)
                self.trial_pause_duration = 4000

                # Number of repetitions of each single image
                self.repetition_count = 5
                self.subtrial_count = self.repetition_count * self.max_photos

                # Duration of the stimulus
                self.stimulation_duration = 175

                # ISI (SOA = ISI + Stimulus Duration)
                self.inter_stimulus_duration = 100

                # Number of images highlighted at a time
                self.highlight_count = 1

                # nr of subtrials for displaying images
                self.subtrials_per_frame = 12


                # switch for effect
                self.rotation = True
                self.brightness = True
                self.enlarge = True
                self.mask = True

                self.viewer = None

                # Highlight order is loaded from file or is randomly generated
                p = os.path.join(os.getcwd(), File_Path)
                if os.path.exists(p):
                        preloaded_highlight_indexes = load_highlights.load2(p, self.subtrial_count, self.highlight_count)
                        print "Loading highlights from highlights.csv!"
                        self.highlight_indexes = preloaded_highlight_indexes
                else:
                        self.highlight_indexes = []
                        for i in range(self.trial_count):
                                self.highlight_indexes.append([])
                                indexes = {}
                                for j in range(self.subtrial_count):
                                        if len(indexes) == 0:
                                                for x in range(self.max_photos):
                                                        indexes[x] = x
                                        new_indexes = random.sample(indexes, self.highlight_count)
                                        for ni in new_indexes:
                                                del indexes[ni]
                                        self.highlight_indexes[i].append(new_indexes)

                self._subtrial_pause_elapsed = 0
                self._subtrial_stimulation_elapsed = 0
                self._inter_stimulus_elapsed = 0
                self._trial_elapsed = 0

                self.MARKER_START = 20
                self.HIGHLIGHT_START = 120
                self.RESET_STATES_TIME = 100

                self._state = STATE_INITIAL

                self._current_trial = -1
                self._current_subtrial = 0

                self._finished = False

                self._stimulus_active = False
                self._markers_sent = False
                self._markers_elapsed = 0
                self._last_marker_sent = 0
                self._current_highlights =  None
                self._current_highlights_index = 0
                self._last_highlight = -1
                self._display_elapsed = 0

                self._in_pre_highlight_pause = False

                self.highlight_all_selected = True
                self._subtrial_scores_received = False
                self.startup_sleep = 1

                self.udp_markers_enable = True #_udp_markers_socket error
                self._markers_reset = False # _markers_reset error
                self._skip_cycle = False

                # Must be called for initialization reasons
                self._on_play()

                # Initialize a second thread in which the main_loop is started
                t = Thread(target=self.main_loop, args=())
                t.start()

        #initialize opengl with a simple ortho projection
        def init_opengl(self):
                glClearColor(0,0,0, 1.0)
                glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
                glMatrixMode(GL_PROJECTION)
                glLoadIdentity()
                glOrtho(0, self.w, 0, self.h, -1, 500)
                glMatrixMode(GL_MODELVIEW)

                #enable texturing and alpha
                glEnable(GL_TEXTURE_2D)
                glEnable(GL_BLEND)
                glEnable(GL_LINE_SMOOTH)

                glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

        # Initialise pygame, and load the fonts
        def init_pygame(self,w,h):
                pygame.init()
                os.environ['SDL_VIDEO_WINDOW_POS'] = "%d,%d" % (self.screenPos[0], self.screenPos[1])
                default_font_name = pygame.font.match_font('bitstreamverasansmono', 'verdana', 'sans')
                if not default_font_name:
                        self.default_font_name = pygame.font.get_default_font()
                self.default_font = pygame.font.Font(default_font_name, 64)
                self.small_font = pygame.font.Font(default_font_name, 12)

                self.screen = pygame.display.set_mode((w,h) , pygame.OPENGL|pygame.DOUBLEBUF)
                #store screen size
                self.w = self.screen.get_width()
                self.h = self.screen.get_height()

                self.init_opengl()
                self.glfont = GLFont(self.default_font, (255,255,255))

        #initialise any surfaces that are required
        def init_surfaces(self):
                pass

        # init routine, sets up the engine, then enters the main loop
        def p300_setup(self):
                self.init_pygame(self.screen_w,self.screen_h)
                self.clock = pygame.time.Clock()
                self.start_time = time.clock()
                self.init_surfaces()
                self.photos = PhotoSet(self.max_photos)
                tick = False
                if self.online_mode or self.highlight_all_selected:
                        tick = True
                self.viewer = P300PhotoViewer(self.photos, self.highlight_indexes, self.w, self.h, self.row, self.col, tick)
                self.fps = 60
                self.phase = 0

                #self.main_loop()

        # handles shutdown
        def quit(self):
                pygame.quit()
                sys.exit(0)

        def draw_paused_text(self):
                size = self.glfont.get_size("Paused")
                #size = [1450,800]
                position = ((self.w-size[0])/2, (self.h-size[1])/2)
                glPushMatrix()
                glTranslatef(position[0], position[1], 0)
                self.glfont.render("Paused")
                glPopMatrix()

        def flip(self):
                # clear the transformation matrix, and clear the screen too
                glMatrixMode(GL_MODELVIEW)
                glLoadIdentity()
                glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
                if self._state != STATE_INITIAL:
                        self.viewer.render(self.w, self.h, self.rotation, self.brightness, self.enlarge, self.mask)
                else:
                        glEnable(GL_TEXTURE_2D)
                        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
                        glColor3f(1.0, 1.0, 1.0)
                        if self._state == STATE_INITIAL:
                                self.draw_paused_text()
                pygame.display.flip()

        def tick(self):
                self.elapsed = self.clock.tick(self.fps)
                self.handle_key_events()
                self.check_state()
                if self._stimulus_active:
                        self.viewer.update(self._current_trial, self._current_subtrial)
                self.flip()

        def play_tick(self):
                pass

        def get_indexes(self):
                self.viewer.update(self._current_trial, self._current_subtrial)
                state = self.viewer.stimulation_state.transpose()
                self._current_highlights = []
                for x in range(self.row):
                        for y in range(self.col):
                                if state[x][y]:
                                        # TODO 6 might be wrong and not modular (maybe numcols?)
                                        self._current_highlights.append((x*6)+y)
                self._current_highlights_index = 0

        def handle_start_trial(self):
                # Pre Trial Handle:
                # - send trial start marker
                # - highlight image for 1 second
                # - pause for 2000ms
                # - reset current subtrial to 0
                # - change state to STATE_SUBTRIAL

                # If the time to wait before showing the target is already elapsed
                if self._trial_elapsed >= self.trial_pre_highlight_duration and not self._in_pre_highlight_pause:
                        self._in_pre_highlight_pause = True
                        if not self.online_mode:
                                self.send_udp(P300_START_TRIAL)
                        self.send_parallel(P300_START_TRIAL)

                        # send marker for selected image
                        time.sleep(0.02)
                        if not self.online_mode:
                                self.send_udp(self.HIGHLIGHT_START)

                self._trial_elapsed += self.elapsed

                # If the pause before showing and the time for showing the target are both elapsed:
                # Clear the highlighting
                if self._trial_elapsed > (self.trial_highlight_duration + self.trial_pre_highlight_duration):
                        self.viewer.clear_highlight()

                # If the pause before, the highlighting itself and the pause after the highlighting are all elapsed:
                # Set state to STATE_SUBTRIAL
                if self._trial_elapsed > (self.trial_pause_duration + self.trial_highlight_duration + self.trial_pre_highlight_duration):
                        self._state = STATE_REPETITION
                        self._trial_elapsed = 0
                        self._current_subtrial = 0
                        self._subtrial_stimulation_elapsed = 0
                        self._subtrial_pause_elapsed = 0
                        self._finished = False

        def handle_repetition(self):
                # send start marker
                # get stimulation order indexes
                # send marker depending on target/ non-target presentation
                # change state to either:
                #       - STATE_DISPLAY_IMAGE (if option to show result of target identification)
                #       - STATE_BETWEEN_TRIALS

                self._subtrial_stimulation_elapsed += self.elapsed
                self._subtrial_pause_elapsed += self.elapsed

                first_marker = False
                if self._subtrial_stimulation_elapsed > self.stimulation_duration:
                        self._stimulus_active = False
                else:
                        self._stimulus_active = True
                        if not self._markers_sent:
                                self._markers_sent = True
                                first_marker = True

                                # send first special marker
                                self.send_parallel(self.MARKER_START)
                                self._markers_reset = False

                if not first_marker and not self._current_highlights:
                        self.get_indexes()
                        if self.online_mode:
                                #self.send_udp('%d\n' % self.MARKER_START)
                                self.send_udp(self.MARKER_START)
                        else:
                                if self._current_target in self._current_highlights:
                                        #self.send_udp('S101\n')
                                        self.send_udp(101)
                                else:
                                        #self.send_udp('S  1\n')
                                        self.send_udp(1)

                elif not first_marker and self._current_highlights and self._current_highlights_index < len(self._current_highlights):
                        if not self._skip_cycle:
                                # if this was the highlighted image
                                if self._current_highlights[self._current_highlights_index] == self._last_highlight and not self.online_mode:
                                        self.send_parallel(self.HIGHLIGHT_START+1+int(self._last_highlight))
                                else:
                                        self.send_parallel(self.MARKER_START+1+self._current_highlights[self._current_highlights_index])
                                self._current_highlights_index+=1
                                self.markers_elapsed = 0
                                self._skip_cycle = True
                        else:
                                self._skip_cycle = False

                if self._subtrial_pause_elapsed >= self.RESET_STATES_TIME and not self._markers_reset and not self.online_mode:
                        #self.send_udp('S  0\n')
                        self.send_udp(0)
                        self._markers_reset = True

                if self._subtrial_pause_elapsed >= self.stimulation_duration + self.inter_stimulus_duration:
                        # move on to next subtrial
                        self._current_subtrial += 1
                        self._subtrial_stimulation_elapsed = 0
                        self._subtrial_pause_elapsed = 0
                        self._stimulus_active = False
                        self._markers_elapsed = 0
                        self._markers_sent = False
                        self._skip_cycle = False
                        self._current_highlights = None

                        # Subtrial is over
                        if self._current_subtrial >= self.subtrial_count:
                                self._display_elapsed = 0
                                self._state = STATE_INITIAL
                                self._trial_elapsed = 0

        def handle_initial(self):
                if not self._finished:
                        self.send_udp(P300_END_EXP)
                        self.send_parallel(P300_END_EXP)
                        self._finished = True

        def check_state(self):
                if self._state == STATE_STARTING_TRIAL:
                        self.handle_start_trial()
                elif self._state == STATE_REPETITION:
                        self.handle_repetition()
                elif self._state == STATE_INITIAL:
                        self.handle_initial()
                else:
                        print "*** Unknown state ***"

        def keyup(self,event):
                if event.key == K_ESCAPE:
                        self.quit()
                if event.key == K_s:
                        self.viewer.set_highlight(random.randint(0,24))
                if event.key== K_c:
                        self.viewer.clear_highlight()
                if event.key == K_e:
                        self.viewer.add_selected_image(random.randint(0, self.max_photos), True)

        def handle_key_events(self):
            # Handles key presses
                for event in pygame.event.get():
                        if event.type==KEYDOWN:
                                if event.key==K_ESCAPE:
                                        self.quit()
                        if event.type==KEYUP:
                                self.keyup(event)
                        if event.type == QUIT:
                                self.quit()

        def on_control_event(self,data):
            pass

        def on_interaction_event(self, data):
            pass

        def main_loop(self):
                """
                Calls tick repeatedly.

                Additionally it calls either :func:`pause_tick` or :func:`play_tick`,
                depending if the Feedback is paused or not.
                """
                self.p300_setup()
                print "Initialised!"
                time.sleep(self.startup_sleep)
                self.send_parallel(P300_START_EXP) # exp start marker
                # manually update state
                self._state = STATE_INITIAL
                self._running = True

                while self._running:
                        self.tick()

        def startBrowser(self):
                self.on_init()

        def startStimulation(self,target_idx):
                self._state = STATE_STARTING_TRIAL
                self._finished = False
                self._current_target = target_idx

        def on_play(self):
                pass


if __name__ == "__main__":
        # simulate pyff for rapid testing
        os.chdir("../..")
        p = VisualAphasiaStimulator()
        p.startBrowser()


        while True:
            p.startStimulation(2)
            for i in range(1,16):
                time.sleep(1)
                print "Sek ",i




