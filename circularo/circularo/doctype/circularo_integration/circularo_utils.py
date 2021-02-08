# -*- coding: utf-8 -*-
# Copyright (c) 2021, Circularo and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import requests


def create_circularo_url(base_url, url, query_parameters=None):
    """
    Creates endpoint URL

    :param base_url: Base of the URL
    :type base_url: str
    :param url: Endpoint path
    :type url: str
    :param query_parameters: Optional query parameters
    :type query_parameters: dict
    :return:
    """
    my_url = base_url + "api/v1/" + url

    if type(query_parameters) is dict:
        first = True
        for key, value in query_parameters.items():
            if first:
                my_url = my_url + "?"
            else:
                my_url = my_url + "&"

            my_url = my_url + key + "=" + value

    return my_url


def call_rest_api(method, url, post_parameters=None, file_parameters=None, json_decode=True):
    """
    Performs request

    :param method: Request method
    :type method: str
    :param url: Request URL
    :type url: str
    :param post_parameters: Optional POST body parameters
    :type post_parameters: dict | None
    :param file_parameters: Optional file parameters
    :type file_parameters: dict
    :param json_decode: Automatically decode JSON?
    :type json_decode: bool
    :return:
    """
    my_function = getattr(requests, method)
    r = my_function(url, json=post_parameters, files=file_parameters)

    r.raise_for_status()

    if json_decode:
        return r.json()
    else:
        return r
