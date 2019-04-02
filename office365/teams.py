import logging
import json
import textile

from .attachment import Attachment

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)


class Teams(object):

	def __init__(self, inbox, group = None, channel = None):
		""" Keyword Arguments:
			inbox (default = None) -- Takes inbox object that manages all communication

		"""
		self.inbox = inbox


	# Getting Information from JSON Part


