#!/usr/bin/env python

"""The setup script."""

from setuptools import setup, find_packages

with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('HISTORY.rst') as history_file:
    history = history_file.read()

requirements = [
    'ijson',
    'lark-parser',
    'orjson==3.3.1',
    'psycopg2-binary',
    'tabulate',
    'typer'
]

setup_requirements = ['pytest-runner', ]

test_requirements = ['pytest>=3', ]

setup(
    author="IBM Security",
    author_email='pcoccoli@us.ibm.com',
    python_requires='>=3.6',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
    description="Columnar storage for STIX 2.0 observations.",
    entry_points={
        'console_scripts': [
            'firepit=firepit.cli:app',
            'splint=firepit.splint:app',
        ],
    },
    install_requires=requirements,
    license="Apache Software License 2.0",
    long_description=readme + '\n\n' + history,
    include_package_data=True,
    keywords='firepit',
    name='firepit',
    packages=find_packages(include=['firepit', 'firepit.*']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/IBM/firepit',
    version='1.0.12',
    zip_safe=False,
)
