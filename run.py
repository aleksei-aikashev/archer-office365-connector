import logging
import time
import getpass
from rsa_archer.archer_instance import ArcherInstance

import templates.templates as temp
from office365.inbox import Inbox

import pymsteams


from urllib3 import disable_warnings, exceptions
disable_warnings(exceptions.InsecureRequestWarning)  # Suppress InsecureRequestWarning

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)-8s %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
log = logging.getLogger(__name__)

period = 5  # in seconds, how often we are checking emails
second_period = 120  # in periods, right now its 10 minutes
perioud_counter = 0

client_id = "" # register an application here https://apps.dev.microsoft.com/

client_secret = getpass.getpass(prompt="Client secret for O365 application: ")
archer_pass = getpass.getpass(prompt="Archer api user password: ")

inbox_instance = Inbox(client_id, client_secret)
inbox_instance.set_filter("IsRead eq false").from_folder("Incidents")

archer_instance = ArcherInstance("url", "instance", "username", archer_pass)
archer_instance.from_application("Incidents")
archer_instance.build_unique_value_to_id_mapping("Incidents", "Incident_ID", "INC-")


ms_teams = pymsteams.connectorcard("webhook")


def get_attacments(attachments):
	attachment_ids = []
	for att in attachments:
		file = att.get_base64()
		name = att.get_name()
		if (not file) or (not name):
			name = "Error"
			file = """RXJyb3IsIHBsZWFzZSByZXNlbmQgZmlsZSBpbiB6aXAgZm9ybWF0LiBUaGlzIHR5cGVzIG9mIGZp
								bGVzIGFyZSBub3QgYWNjZXB0ZWQgYnkgQXJjaGVyIGFzIGlzLg=="""
		id = archer_instance.post_attachment(name, file)
		attachment_ids.append(id)
	return attachment_ids

messages = []
attachments = []

while True:
	if perioud_counter == second_period:
		perioud_counter = 0

	try:
		messages = inbox_instance.fetch(12)
	except Exception as e:
		log.error("fetching emails didn't work,exception: %s", e)
		continue

	for message in messages:
		subject = message.get_subject()
		sender = message.get_sender_json()
		sender_email = message.get_sender_email()
		sender_name = message.get_sender_name()
		attachments = message.get_attachments()

		sub_record_json = {"author_of_email": sender_name}

		log.info("Processing email: %s", subject)

		try:
			body = message.get_body()
			sub_record_json["Comments"] = body
			if attachments:
				sub_record_json["Attachments"] = get_attacments(attachments)

			sub_record_id = archer_instance.create_sub_record(sub_record_json, "Comments")

			transformed_body = "<p>Reporter: " + str(sender) + "</p>" \
															   "<p>Reported the following:</p><p>&nbsp;</p>" + body

			record_id = archer_instance.create_content_record(
					{"Incident Summary": subject, "Reporter email": sender_email,
					 "Incident Details": transformed_body, "Comments": sub_record_id})
			created_record = archer_instance.get_record(record_id)
			incident_id = created_record.get_sequential_id()
			archer_instance.add_record_id_to_mapping(incident_id, record_id, "INC-")

			appendix = "(#INC-" + str(incident_id) + ") (Archer) "

			message.mark_as_read()
			message.return_reply_all_draft()
			message.append_text_to_subject(appendix)
			message.set_reply_body("")
			message.update_message()
			message.send_message()

			#MS Teams notification
			ms_teams.title(f"New #INC-{incident_id}: {subject}")
			ms_teams.text(f"{body}")
			ms_teams.addLinkButton(f"#INC-{incident_id}", f"https://xxxx.com/RSAArcher/default.aspx?requestUrl=..%2fGenericContent%2fRecord.aspx%3fid%3d{record_id}%26moduleId%3d75")


		except Exception as e:
			log.error("Error during New record creation: %s. Next email...",e)
			continue


	time.sleep(period)
	perioud_counter += 1
