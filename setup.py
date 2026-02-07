from setuptools import setup

setup(
    name='ofek-aws-cli',
    version='0.1',
    py_modules=['main', 'utils', 'ec2', 's3', 'route53', 'cleanup_ops'],
    install_requires=[
        'Click',
        'boto3',
        'rich',
        'streamlit',
        'setuptools'
    ],
    entry_points='''
        [console_scripts]
        ofek-cli=main:cli
        ec2=main:ec2
        s3=main:s3
        route53=main:route53
    ''',
)