'''
Setup for es-metrics-aws-cur-app package.
'''
# Always prefer setuptools over distutils
from setuptools import setup, find_packages
from os import path

HERE = path.abspath(path.dirname(__file__))

PROJECT = 'grape'

# Get the long description from the README file
with open(path.join(HERE, 'README.md'), encoding='utf-8') as f:
    LONG_DESCRIPTION = f.read()

# Get the version.
with open(f'{PROJECT}/__version__') as vifp:
    VERSION = vifp.read().strip()

# Run the setup.
setup(
    name=PROJECT,
    version=VERSION,
    description='Grafana Model Development Tool',
    long_description=LONG_DESCRIPTION,
    long_description_content_type='text/markdown',
    url='https://github.com/eSentire/grape',
    author='eSentire',
    author_email='open-source@esentire.com',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Information Technology',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        ],
    keywords='grafana postgres modeling prototype',
    python_requires='>=3.9, <4',
    install_requires=['docker',
                      'psycopg2-binary',
                      'PyYAML',
                      'requests'],
    packages=find_packages(),
    package_data={PROJECT: ['__version__']},
    license='MIT',
    entry_points={
        'console_scripts': [
            # One interface to rule them all.
            'grape=grape.cli:main',
        ],
    },
)
