# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

with open("requirements.txt") as f:
	install_requires = f.read().strip().split("\n")

# get version from __version__ variable in declaracion_mensual/__init__.py
from declaracion_mensual import __version__ as version

setup(
	name="declaracion_mensual",
	version=version,
	description="Cálculos para declaración mensual",
	author="Baltazar Rodriguez",
	author_email="marmotae@gmail.com",
	packages=find_packages(),
	zip_safe=False,
	include_package_data=True,
	install_requires=install_requires
)
