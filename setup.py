# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

version = '1.0.0'

setup(
    name='circularo',
    version=version,
    description='Example integration of open source DMS to Circularo esigning platform.',
    author='Circularo',
    author_email='info@circularo.com',
    packages=find_packages(),
    zip_safe=False,
    include_package_data=True,
    install_requires=("frappe",),
)
