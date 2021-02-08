# -*- coding: utf-8 -*-
# Copyright (c) 2021, Circularo and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import io
import frappe
from frappe.model.document import Document
from frappe.utils.pdf import get_pdf
from frappe.utils.file_manager import save_file
from PyPDF2 import PdfFileReader
from circularo.circularo.doctype.circularo_integration.circularo_utils import create_circularo_url, call_rest_api

# Sign during document creation
QUICK_SIGN = True

# Default Circularo parameters
DEFAULT_DOCUMENT_TYPE = "d_default"
DEFAULT_DEFINITION_TYPE = "ext"
DEFAULT_WORKFLOW_TYPE = "wf_archive"

# Required user rights
REQUIRED_RIGHTS = ["use_file_management", "use_document_management"]


class CircularoIntegration(Document):
	"""
	Circularo Integration DocType backend
	Represents Circularo integration settings
	"""
	def validate(self):
		"""
		If integration is not enabled, delete API token

		:return:
		"""
		if not self.enabled:
			self.logout_api_token()

	def get_preview_url(self, document_id):
		"""
		Get Circularo document preview URL

		:param document_id: Circularo document ID
		:type document_id: str
		:return: Circularo preview URL
		"""
		base_url = self.circularo_url
		document_type = self.circularo_document_type

		return base_url + "#!/home/" + document_type + "?select=" + document_id + "&selectType=" + document_type + "&modal=preview"

	def get_sign_url(self, document_id):
		"""
		Get Circularo sign URL

		:param document_id: Circularo document ID
		:type document_id: str
		:return: Circularo sign URL
		"""
		base_url = self.circularo_url
		document_type = self.circularo_document_type

		return base_url + "#!/signPrepare?mode=create&documentId=" + document_id + "&documentType=" + document_type + "&step=choose"

	def logout_api_token(self):
		"""
		Logout Circularo API Token

		:return:
		"""
		if self.circularo_api_token is not None:
			try:
				logout_url = create_circularo_url(self.circularo_url, "api/key/" + self.circularo_api_token)
				call_rest_api("delete", logout_url)
			except:
				pass

		self.circularo_api_token = None

	def is_enabled(self, doctype, view, docname):
		"""
		Check if Circularo integration is enabled for current doctype and view

		:param doctype: Frappe DocType
		:type doctype: str
		:param view: Frappe View
		:type view: str
		:param docname: Frappe DocName
		:type docname: str
		:return: True if enabled
		"""
		# Do not show for Circularo Documents (history)
		if doctype == "Circularo Documents":
			return False

		# Check if enabled
		if self.enabled != 1:
			return False

		# Check if API token exists
		if self.circularo_api_token is None:
			return False

		# Check if enabled in given view
		if (view.lower() == "form") and (self.show_in_form_view != 1):
			return False
		elif (view.lower() == "list") and (self.show_in_list_view != 1):
			return False

		if self.show_in_all_doctypes == 0:
			# Not enabled for all DocTypes
			split_doctypes = self.show_in_doctypes.split(",")
			my_doctypes = []
			for doc in split_doctypes:
				my_doctypes.append(doc.lower().strip())

			check_doctype = doctype.lower().strip()
			if check_doctype not in my_doctypes:
				return False

		elif (view.lower() == "form") and (self.show_in_single == 0):
			# Enabled for all DocTypes without singletons
			issingle = frappe.get_doc(doctype, docname)._meta.issingle
			if issingle == 1:
				return False

		#  Pass
		return True


@frappe.whitelist()
def restore_settings():
	"""
	Restore Circularo advanced settings

	:return:
	"""
	circularo_integration = frappe.get_doc("Circularo Integration")
	circularo_integration.circularo_document_type = DEFAULT_DOCUMENT_TYPE
	circularo_integration.circularo_definition_type = DEFAULT_DEFINITION_TYPE
	circularo_integration.circularo_workflow_type = DEFAULT_WORKFLOW_TYPE
	circularo_integration.send_to_email = 0
	circularo_integration.save()

	return {
		"status": 0,
		"message": {}
	}


@frappe.whitelist()
def is_enabled(doctype, view, docname):
	"""
	Check if Circularo integration is enabled for given DocType and view

	:param doctype: Frappe DocType
	:type doctype: str
	:param view: Frappe View
	:type view: str
	:param docname: Frappe DocName
	:type docname: str
	:return:
	"""
	circularo_integration = frappe.get_doc("Circularo Integration")
	if circularo_integration.is_enabled(doctype, view, docname):
		return {
			"status": 0,
			"message": {}
		}
	else:
		return {
			"status": 1,
			"message": {}
		}


@frappe.whitelist()
def create_api_token(url, tenant, email, password):
	"""
	Create Circularo API Token

	:param url: Circularo server URL
	:type url: str
	:param tenant: Circularo tenant
	:type tenant: str
	:param email: Circularo user e-mail
	:type email: str
	:param password: Circularo user password
	:type password: str
	:return:
	"""
	if not url.endswith("/"):
		url = url + "/"

	try:
		_check_ping(url)
		_check_tenant(url, tenant)

		# Log in user
		token_info = _login_to_circularo(url, tenant, email, password)
		token = token_info.get("token")

		# Check if required rights are presented
		user_rights = token_info.get("rights")
		for required_right in REQUIRED_RIGHTS:
			if required_right not in user_rights:
				_logout_user(url, token)
				frappe.throw("User doesn't have required right '" + required_right + "'.")

		# Check if signature is presented
		config = token_info.get("user").get("config")
		if ("signature" not in config) or (not isinstance(config.get("signature"), list)) or \
					(len(config.get("signature")) < 1) or ("imageId" not in config.get("signature")[0]):
			_logout_user(url, token)
			frappe.throw("User doesn't have any signature.")
		signature_id = config.get("signature")[0].get("imageId")

		# Create long term API token
		api_token = _create_api_token(url, token)
		_logout_user(url, token)

		circularo_integration = frappe.get_doc("Circularo Integration")
		circularo_integration.circularo_url = url
		circularo_integration.circularo_tenant = tenant
		circularo_integration.circularo_api_token = api_token
		circularo_integration.signature_id = signature_id

		circularo_integration.save()
	except Exception as e:
		return {
			"status": 1,
			"message": str(e)
		}

	return {
		"status": 0,
		"message": "API Token successfully created."
	}


@frappe.whitelist()
def remove_api_token():
	"""
	Remove Circularo API Token

	:return:
	"""
	circularo_integration = frappe.get_doc("Circularo Integration")
	circularo_integration.logout_api_token()
	circularo_integration.save()

	return {
		"status": 0,
		"message": "Circularo API token has been removed."
	}


@frappe.whitelist()
def upload_file(doctype, docname):
	"""
	Upload Frappe document into Circularo

	:param doctype: Frappe DocType
	:type doctype: str
	:param docname: Frappe DocName
	:type docname: str
	:return: Circularo file info
	"""
	try:
		circularo_integration = frappe.get_doc("Circularo Integration")
		create_file_url = create_circularo_url(circularo_integration.circularo_url, "files/saveFile", {"token": circularo_integration.circularo_api_token})

		# Crete PDF file from document
		pdf_bytes, num_pages = _print_to_pdf(doctype, docname)
		r = call_rest_api("post", create_file_url, {"fileName": docname + ".pdf"}, {"file": pdf_bytes})

		return {
			"status": 0,
			"message": {
				"file_id": r.get("file").get("hash"),
				"num_pages": num_pages
			}
		}

	except Exception as e:
		return {
			"status": 1,
			"message": str(e)
		}


@frappe.whitelist()
def create_document(doctype, docname, file_hash, sign_page, is_sign, is_autosign):
	"""
	Create Circularo document from uploaded file

	:param doctype: Frappe DocType
	:type doctype: str
	:param docname: Frappe DocName
	:type docname: str
	:param file_hash: Circularo file ID
	:type file_hash: str
	:param sign_page: Number of PDF fie pages
	:type sign_page: int
	:param is_sign: 1 if is sign action, 0 otherwise
	:type is_sign: int
	:param is_autosign: 1 if is autosign action, 0 otherwise
	:type is_autosign: int
	:return: Circularo document info
	"""
	try:
		is_sign = int(is_sign)
		is_autosign = int(is_autosign)

		circularo_integration = frappe.get_doc("Circularo Integration")
		create_document_url = create_circularo_url(circularo_integration.circularo_url, "documents", {"token": circularo_integration.circularo_api_token})

		# Base JSON to create document
		json = {
			"body": {
				"documentType": circularo_integration.circularo_document_type,
				"documentTitle": docname,
				"pdfFile": {
					"content": file_hash
				}
			},
			"definitionType": circularo_integration.circularo_definition_type,
			"workflow": circularo_integration.circularo_workflow_type
		}

		if is_autosign == 1:
			# Sign document

			if QUICK_SIGN:
				# Quick sign (in one request)

				# Append new data to existing JSON
				json["optionalData"] = {
					"signatures": [{
						"type": "signature",
						"blob": circularo_integration.signature_id,
						"page":  sign_page,
						"position": {
							"percentX": 0.53,
							"percentY": 0.81,
							"percentWidth": 0.40,
							"percentHeight": 0.10
						},
						"decorationType": "empty"
					}],
					"annotations": [{
						"align": "left",
						"backgroundColor": "#ffffff",
						"bold": False,
						"color": "#000000",
						"fontSize": 10,
						"page": sign_page,
						"position": {
							"percentX": 0.55,
							"percentY": 0.92,
							"percentWidth": 0.35,
							"percentHeight": 0.015
						},
						"subtype": "docId",
						"text": "{{{documentId}}}"
					}]
				}
				r = call_rest_api("post", create_document_url, json)
				document_id = r.get("results")[0].get("documentId")

			else:
				# "Slow" sign

				# 1. Create document
				r = call_rest_api("post", create_document_url, json)
				document_id = r.get("results")[0].get("documentId")

				# 2. Check document version
				document_version = str(_get_document_details(document_id).get("_version"))

				# 3. Sign document
				_sign_document(document_id, document_version, sign_page)

		else:
			# Not signing
			r = call_rest_api("post", create_document_url, json)
			document_id = r.get("results")[0].get("documentId")

		preview_url = circularo_integration.get_preview_url(document_id)
		sign_url = circularo_integration.get_sign_url(document_id)

		# Create history record
		history_record = frappe.new_doc("Circularo Documents")
		history_record.initialize(doctype, docname, document_id, preview_url, sign_url, is_sign, is_autosign)
		history_record.save()

		history_url = history_record.get_url()
		history_name = history_record.name

		return {
			"status": 0,
			"message": {
				"docname": docname,
				"document_id": document_id,
				"preview_url": preview_url,
				"sign_url": sign_url,
				"history_url": history_url,
				"history_name": history_name
			}
		}

	except Exception as e:
		return {
			"status": 1,
			"message": str(e)
		}


@frappe.whitelist()
def download_file(history_name, download_manual_sign):
	"""
	Download PDF file from Circularo

	:param history_name: Circularo documents (history) record DocName
	:type history_name: str
	:param download_manual_sign: If manual sign action was chosen, use 1 to download signed file or 0 to return immediately
	:type download_manual_sign: num
	:return: Info if file was downloaded
	"""
	try:
		download_manual_sign = int(download_manual_sign)
		history_record = frappe.get_doc("Circularo Documents", history_name)

		if (download_manual_sign == 0) and (history_record.is_sign == 1) and (history_record.is_autosign == 0):
			# Manual sign and we don't want to download -> return
			return {
				"status": 0,
				"message": {
					"downloaded": False
				}
			}

		# Fetch document details
		document_details = _get_document_details(history_record.target_document_id)
		file_id = document_details.get("pdfFile").get("content")
		is_signed = document_details.get("isSigned")

		if (download_manual_sign == 1) and (not is_signed) and (history_record.is_sign == 1) and (history_record.is_autosign == 0):
			# Manual sign and we want to download, but not signed yet -> return sign URL
			return {
				"status": 0,
				"message": {
					"downloaded": False,
					"sign_url": history_record.circularo_sign_url
				}
			}

		file_name = history_record.target_docname + ".pdf"
		# Download signed PDF file from Circularo
		file_data = _download_file(file_id)
		# Save downloaded file
		saved_file = save_file(file_name, file_data.content, None, None)

		# Update history record
		history_record.file_url = saved_file.file_url
		history_record.is_downloaded = True
		history_record.save()

		circularo_integration = frappe.get_doc("Circularo Integration")
		if (history_record.is_autosign == 1) and (circularo_integration.send_to_email == 1):
			# Send e-mail with signed document
			recipient = get_email(frappe.session.user)
			frappe.sendmail(
				recipients=recipient,
				subject="Document signed",
				message="Your document has been signed.",
				attachments=[{
					"fname": file_name,
					"fcontent": file_data.content
				}],
				delayed=False)

		return {
			"status": 0,
			"message": {
				"downloaded": True
			}
		}

	except Exception as e:
		return {
			"status": 1,
			"message": str(e)
		}


def get_email(user):
	"""
	Return user's e-mail address

	:param user: User
	:type user: str
	:return: E-mail address
	"""
	return frappe.db.get_value("User", user, ["email"], as_dict=True).get("email")


def _download_file(file_id):
	"""
	Download file from Circularo

	:param file_id: Circularo file ID
	:type file_id: str
	:return: Downloaded file bytes
	"""
	circularo_integration = frappe.get_doc("Circularo Integration")
	download_file_url = create_circularo_url(circularo_integration.circularo_url, "files/loadFile/hash/" + file_id, {"token": circularo_integration.circularo_api_token})

	return call_rest_api("get", download_file_url, None, None, False)


def _get_document_details(document_id):
	"""
	Get details about Circularo document

	:param document_id: Circularo document id
	:type document_id: str
	:return: Document information
	"""
	circularo_integration = frappe.get_doc("Circularo Integration")
	get_document_url = create_circularo_url(circularo_integration.circularo_url, "documents/" + document_id, {"token": circularo_integration.circularo_api_token})

	r = call_rest_api("get", get_document_url)
	return r.get("results")[0]


def _sign_document(document_id, document_version, sign_page):
	"""
	Sign document in Circularo

	:param document_id: Circularo document ID
	:type document_id: str
	:param document_version: Circularo document version
	:type document_version: str
	:param sign_page: Page to be signed
	:type sign_page: int
	:return:
	"""
	circularo_integration = frappe.get_doc("Circularo Integration")
	sign_document_url = create_circularo_url(circularo_integration.circularo_url, "documents/sign/" + document_version, {"token": circularo_integration.circularo_api_token})
	json = {
		"id": document_id,
		"type": circularo_integration.circularo_document_type,
		"signatures": [{
			"type": "signature",
			"blob": circularo_integration.signature_id,
			"page":  sign_page,
			"position": {
				"percentX": 0.53,
				"percentY": 0.81,
				"percentWidth": 0.40,
				"percentHeight": 0.10
			},
			"decorationType": "empty"
		}],
		"annotations": [{
			"align": "left",
			"backgroundColor": "#ffffff",
			"bold": False,
			"color": "#000000",
			"fontSize": 10,
			"page": sign_page,
			"position": {
				"percentX": 0.55,
				"percentY": 0.92,
				"percentWidth": 0.35,
				"percentHeight": 0.015
			},
			"subtype": "docId",
			"text": "{{{documentId}}}"
		}]
	}
	call_rest_api("put", sign_document_url, json)


def _print_to_pdf(doctype, docname):
	"""
	Print Frappe document to PDF

	:param doctype: Frappe DocType
	:type doctype: str
	:param docname: Frappe DocName
	:type docname: str
	:return: PDF file bytes and number of pages
	"""
	html = frappe.get_print(doctype, docname)

	pdf_bytes = get_pdf(html)
	reader = PdfFileReader(io.BytesIO(pdf_bytes))

	return pdf_bytes, reader.getNumPages()


def _check_ping(url):
	"""
	Check if Circularo server pings

	:param url: Circularo server URL
	:type url: str
	:return:
	"""
	ping_url = create_circularo_url(url, "ping")
	try:
		call_rest_api("get", ping_url)
	except:
		frappe.throw("No ping response from server '" + url + "'!")


def _check_tenant(url, tenant):
	"""
	Check if Circularo tenant exists

	:param url: Circularo server URL
	:type url: str
	:param tenant: Circularo tenant
	:type tenant: str
	:return:
	"""
	tenant_url = create_circularo_url(url, "settings", {"tenant": tenant})
	try:
		call_rest_api("get", tenant_url)
	except:
		frappe.throw("Incorrect tenant '" + tenant + "'!")


def _login_to_circularo(url, tenant, email, password):
	"""
	Login user to Circularo

	:param url: Circularo server URL
	:type url: str
	:param tenant: Circularo tenant
	:type tenant: str
	:param email: User e-mail
	:type email: str
	:param password: User password
	:type password: str
	:return: Circularo user token
	"""
	login_url = create_circularo_url(url, "login")
	json = {
		"tenant": tenant,
		"name": email,
		"password": password
	}

	try:
		r = call_rest_api("post", login_url, json)
		return r
	except:
		frappe.throw("Incorrect e-mail or password!")


def _create_api_token(url, token):
	"""
	Create long term Circularo API Token

	:param url: Circularo server URL
	:type url: str
	:param token: Circularo tenant
	:type token: str
	:return: Circularo API Token
	"""
	api_key_url = create_circularo_url(url, "api/key", {"token": token})

	try:
		r = call_rest_api("post", api_key_url)
		return r.get("id")
	except:
		frappe.throw("Unable to create API key!")


def _logout_user(url, token):
	"""
	Logout circularo user

	:param url: Circularo server URL
	:type url: str
	:param token: Circularo tenant
	:type token: str
	:return:
	"""
	try:
		logout_url = create_circularo_url(url, "logout", {"token": token})
		call_rest_api("get", logout_url)
	except:
		pass
