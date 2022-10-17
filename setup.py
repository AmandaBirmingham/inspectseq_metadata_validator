# ----------------------------------------------------------------------------
# Copyright (c) 2022, Amanda Birmingham
#
# Distributed under the terms of the BSD-3-Clause license.
#
# The full license is in the file LICENSE, distributed with this software.
# ----------------------------------------------------------------------------
from setuptools import setup, find_packages


setup(
    name='inspectseq_metadata_validator',
    version="1.0.0",
    license='BSD-3-Clause',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'capture_metadata_locations=src.capture_locations_from_metadata_csv:main',
            'generate_metadata_reports=src.generate_metadata_validation_report:main'
        ]}
)
