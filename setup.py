from setuptools import setup

setup(name='sama',
        version='0.0.1',
        description='Sama Python Client',
        url='https://www.sama.com',
        author='Edward',
        author_email='echan@sama.com',
        license='MIT',
        packages=['sama'],
        install_requires=[
            'retry'
        ])