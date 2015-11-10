from p300_decision import *
from p300_sequence import *

class p300_scorer:
	def __init__(self):
		self.subtrial_count = -1
		self.scores_received = 0
		self.dec = None
		self.seqgen = None
		self.seqdata = None

	def reset_on_new_trial(self, decparams, seqparams):
		self.scores_received = 0
		self.dec = decider()
		self.seqgen = sequenceGenerator()
		self.seqdata = None

		self.dec.set(decparams)
		self.seqgen.set(seqparams)

		self.seqdata = self.seqgen.generate()
		print self.seqdata

	def add_set_of_scores(self, scores):
		self.dec.add_score((scores, self.seqdata[self.scores_received]))
		self.scores_received += 1
		print '>> Received scores for subtrial: %d' % self.scores_received

	def all_scores_received(self):
		return (self.scores_received == len(self.seqdata))

	def sequencedata(self):
		return self.seqdata 

	def query_winner(self):
		return self.dec.query_winner()

