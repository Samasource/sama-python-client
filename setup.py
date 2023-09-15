from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(name='sama',
        version='0.5.11',
        description='Sama Python Client and Databricks Connector',
        long_description=long_description,
        long_description_content_type="text/markdown",
        url='https://www.sama.com',
        author='Edward',
        author_email='echan@samasource.org',
        license=' Apache-2.0 license',
        packages=find_packages(),
        install_requires=[
            'retry',
            'requests'
        ])