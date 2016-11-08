from setuptools import setup, find_packages


with open('README') as f:
    long_description = ''.join(f.readlines()) 
 
setup(
    name='gh_issue_agent',
    version='0.5',
    description='Automatic Labels for GitHub Issues',
    author='Tomas Kvasnicka',
    author_email='nzt4567@gmx.com',
    license='Public Domain',
    url='https://github.com/nzt4567/gh_issue_agent.git',
    packages=find_packages(),
    long_description=long_description,
    classifiers=[
        'Intended Audience :: Developers',
        'License :: Public Domain',
        'Operating System :: POSIX :: Linux',
        'Programming Language :: Python',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5'],
    install_requires=['flask', 'requests', 'click', 'jinja2'],
    setup_requires=['pytest-runner'],
    tests_require=['pytest', 'flexmock', 'betamax'],
    entry_points={
        'console_scripts': [
            'gh_issue_agent = gh_issue_agent.agent:main',
        ],
    },

)

