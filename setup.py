from setuptools import setup

setup(
    name='ofek-aws-cli',
    version='0.1',
    py_modules=['main', 'utils', 'ec2', 's3'], # רשימת הקבצים שלך
    install_requires=[
        'Click',
        'boto3',
        'rich',
    ],
    entry_points='''
        [console_scripts]
        ofek-cli=main:cli
    ''',
)