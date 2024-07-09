from setuptools import setup, find_packages

# Read the dependencies from the requirements.txt file
with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setup(
    name='modal_or_local',
    version='0.1.0',
    description='File and directory utilities for working with modal volumes or the local filesystem',
    author='Paul Wessling',
    author_email='paul@nowfree.org',
    url='https://github.com/eyecantell/modal_or_local',
    license='MIT',
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        'console_scripts': [
            'modal_or_local = modal_or_local.__main__:main',
        ],
    },
)