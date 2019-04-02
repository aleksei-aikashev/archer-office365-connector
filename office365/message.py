import logging
import json
import textile

from .attachment import Attachment

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)


class Message(object):

	def __init__(self, json=None, inbox=None):
		""" Keyword Arguments:
			json (default = None) -- Takes json if you have a pre-existing message to create from.
			this is mostly used inside the library for when new messages are downloaded.
			inbox (default = None) -- Takes inbox object that manages all communication
		"""
		self.json = json
		self.inbox = inbox
		self.has_attachments = json['HasAttachments']
		self.attachments = []
		self.json_updater = {}

	# Getting Information from JSON Part

	def get_sender_json(self):
		return self.json['sender']

	def get_sender_email(self):
		return self.json['sender']['emailAddress']['address']

	def get_sender_name(self):
		try:
			return self.json['sender']['emailAddress']['name']
		except:
			return self.json['sender']

	def get_subject(self):
		return self.json['subject']

	def get_body(self):
		try:
			if self.json['body']['contentType'] == "html":
				return self.json['body']['content']
			else:
				return textile.textile(self.json['body']['content'])
		except:
			log.error("The is no body content in email")
			return ""

	# Editing updater JSON Part

	def add_recipient(self, address, name=None, r_type="to"):
		"""
		:param address: email address
		:param name: Recepient Name
		:param r_type: ould be to,cc,bcc
		:return: self.json_updater
		"""
		if name is None:
			name = address[:address.index('@')]
		self.json[r_type + 'Recipients'].append(
				{'emailAddress': {'address': address, 'name': name}})
		self.json_updater[r_type + 'Recipients'] = {'emailAddress': {}}
		self.json_updater[r_type + 'Recipients'] = self.json[r_type + 'Recipients']

	def remove_recipient(self, email=None):
		"""
		:param email:
		:return: self.json_updater
		"""
		recepient_types = ["to", "cc", "bcc"]
		try:
			for r_type in recepient_types:
				for email_dict in self.json[r_type + 'Recipients']:
					if email_dict['emailAddress']['address'] == email:
						email_dict['emailAddress'].pop("name", None)
						email_dict['emailAddress'].pop("address", None)
		except Exception as e:
			log.info("Cannot remove %s as recepient, %s", email, e)

	def set_reply_body(self, body):
		"""
		:param body: adds this text on top of previous message
		:return: self.json_updater
		"""
		self.json_updater['body'] = {}

		if self.json['body']['contentType'] == "html":
			self.json_updater['body']['content'] = body + self.json['body']['content']
		else:
			self.json_updater['body']['content'] = body + textile.textile(self.json['body']['content'])

		self.json_updater['body']['contentType'] = 'html'

	def set_category(self, category_name):
		"""
		:param category_name: "Red category", "Yellow category", "Green category"
		:return: self.json_updater
		"""

		self.json_updater["categories"] = [category_name]
		self.json_updater["importance"] = "high"
		self.json_updater["inferenceClassification"] = "focused"

	def set_sender(self, name, email):
		"""
		:param name: Sender name
		:param email: Sender email
		:return: self.json_updater
		"""
		self.json_updater["from"] = {"emailAddress": {}}
		self.json_updater["sender"] = {"emailAddress": {}}
		self.json_updater["from"]["emailAddress"]["name"] = name
		self.json_updater["from"]["emailAddress"]["address"] = email
		self.json_updater["sender"]["emailAddress"]["name"] = name
		self.json_updater["sender"]["emailAddress"]["address"] = email

	def append_text_to_subject(self, appendix):
		"""
		:param appendix: add stuff before subject
		:return: self.json_updater
		"""
		self.json_updater['subject'] = str(appendix) + self.json['subject']

	# Actionable Part Involving Inbox Object

	def return_reply_all_draft(self):
		"""
		:return: self.json
		"""
		reply_all_url = self.inbox.url + "/" + self.json['id'] + "/createReplyAll?$select=uniqueBody"

		try:
			response = self.inbox.get_response_POST(reply_all_url)
			self.json = response

		except Exception as e:
			log.info("Response Code: %s and Exception %s", response.status_code, e)

		return self

	def update_message(self, updated_json=None):
		"""
		:param updated_json: by default its self.json_updater
		:return: self.json
		"""
		message_id = self.json["id"]

		if updated_json:
			updated_j = json.dumps(updated_json)
		else:
			updated_j = json.dumps(self.json_updater)

		try:
			response = self.inbox.get_response_PATCH(message_id, updated_j)
			self.json = response

		except Exception as e:
			log.info("Response Code: %s and Exception %s", response.status_code, e)

		return self

	def send_message(self):
		send_url = self.inbox.inbox_url + "/" + self.json['id'] + "/send"

		try:
			response = self.inbox.oauth.post(send_url)

			if response.status_code == 200 or 202:
				log.info("Message has been sent - %s", self.json["subject"])
			else:
				log.error("Email has not been send: %s", response.content)

		except Exception as e:
			log.error("Exception %s", e)

		return self

	def mark_as_read(self):
		isRead = {"isRead": "true"}
		self.update_message(isRead)

		return self

	def fetch_unique_content(self):
		"""
			:return: self
		"""
		message_url = self.inbox.url + "/" + self.json['id'] + "?$select=uniqueBody"

		try:
			response = self.inbox.oauth.get(message_url)
			data = response.content.decode('utf8')
			response_json = json.loads(data)

			self.json['body']['content'] = response_json['uniqueBody']['content']

		except Exception as e:
			log.info("Exception %s", e)

		return self

	def get_attachments(self):
		'''kicks off the process that downloads attachments locally.'''

		if not self.has_attachments:
			log.info('Message has no attachments, skipping out early.')
			return False

		m_url = self.inbox.url + "/" + self.json['id'] + "/attachments"

		try:
			response = self.inbox.oauth.get(m_url)
			json = response.json()
			for att in json['value']:
				self.attachments.append(Attachment(att))
				log.info('Successfully downloaded attachment for: %s.', self.json['subject'])

		except Exception as e:
			log.info('Failed to download attachment for: %s becouse %s', self.json['subject'], e)

		return self.attachments
