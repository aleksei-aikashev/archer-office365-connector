import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)


class Attachment(object):
	'''
	Attachment class is the object for dealing with attachments in your messages.
	'''

	create_url = 'https://outlook.office365.com/api/v1.0/me/messages/{0}/attachments'

	def __init__(self, json):
		'''
		Creates a new attachment class from JSON.
		'''
		self.json = json

	def get_base64(self):
		'''Returns the base64 encoding representation of the attachment.'''
		try:
			return self.json['contentBytes']
		except Exception as e:
			log.error('what? no clue what went wrong in get_base64(), probably no attachment: %s', e)
		return False

	def get_name(self):
		'''Returns the file name.'''
		try:
			return self.json['name']
		except Exception as e:
			log.error('The attachment does not appear to have a name, %s', e)
			return False
