# -*- coding: utf-8 -*-
# Copyright (c) 2021, Circularo and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document

class CircularoDocuments(Document):
	"""
	Circularo Documents DocType backend
	Represents Circularo actions history
	"""
	def initialize(self, doctype, docname, document_id, preview_url, sign_url, is_sign, is_autosign):
		"""
		Initializes Circularo document (history)

		:param doctype: Frappe DocType
		:type doctype: str
		:param docname: Frappe DocName
		:type docname: str
		:param document_id: Circularo document ID
		:type document_id: str
		:param preview_url: Circularo document preview URL
		:type preview_url: str
		:param sign_url: Circularo document sign URL
		:type sign_url: str
		:param is_sign: 1 if was sign action, 0 otherwise
		:type is_sign: int
		:param is_autosign: 1 if was autosign action, 0 otherwise
		:type is_autosign: int
		:return:
		"""
		self.target_docname = docname
		self.target_doctype = doctype
		self.author = frappe.session.user
		self.date = frappe.utils.data.now_datetime()

		self.is_downloaded = False
		self.is_sign = is_sign
		self.is_autosign = is_autosign
		self.target_document_id = document_id
		self.circularo_preview_url = preview_url
		self.circularo_sign_url = sign_url

		self.action = "Archive"
		if is_sign == 1:
			self.action = "Sign"
		if is_autosign == 1:
			self.action = "Automatic sign"

		self.target_url = "/desk#Form/" + doctype
		if docname is not None:
			self.target_url += "/" + docname


@frappe.whitelist()
def get_app_url(doctype, docname):
	"""
	Returns Frappe URL

	:param doctype: Frappe DocType
	:type doctype: str
	:param docname: Frappe DocName
	:type docname: str
	:return:
	"""
	circularo_document = frappe.get_doc(doctype, docname)

	return {
		"status": 0,
		"message": circularo_document.target_url
	}


@frappe.whitelist()
def get_circularo_url(doctype, docname):
	"""
	Returns Circularo preview URL

	:param doctype: Frappe DocType
	:type doctype: str
	:param docname: Frappe DocName
	:type docname: str
	:return:
	"""
	circularo_document = frappe.get_doc(doctype, docname)
	circularo_url = circularo_document.circularo_preview_url

	return {
		"status": 0,
		"message": circularo_url
	}


@frappe.whitelist()
def view_file(doctype, docname):
	"""
	Returns PDF file url

	:param doctype: Frappe DocType
	:type doctype: str
	:param docname: Frappe DocName
	:type docname: str
	:return:
	"""
	circularo_document = frappe.get_doc(doctype, docname)
	file_url = circularo_document.file_url

	return {
		"status": 0,
		"message": file_url
	}

