Doctest
=======

.. testsetup::

   import gh_issue_agent
   import pytest
   import configparser
   from flexmock import flexmock
   import os
   from pprint import pprint

   mock = flexmock(os.path)
   mock.should_call('isfile')
   mock.should_receive('isfile').with_args('auth-test.cfg').and_return(True)
   mock.should_receive('isfile').with_args('label-test.cfg').and_return(True)

   mock = flexmock(configparser.ConfigParser)
   mock.should_call('sections')
   mock.should_receive('sections').and_return(['github', 'labels'])
   mock.should_call('items')
   mock.should_receive('items').with_args('github').and_return({'token': 'XXXXXXXXXX'})
   mock.should_receive('items').with_args('labels').and_return({'.*bug.*': 'possible_bug', '.*now.*': 'ASAP'})


.. doctest::

   >>> pprint(gh_issue_agent.parse_args('mi-pyt-label-robot/r1', 'auth-test.cfg', 'label-test.cfg', 'take-a-look-personally', True, None))
   {'comments': True,
    'default_label': 'take-a-look-personally',
    'labels': {'.*bug.*': 'possible_bug', '.*now.*': 'ASAP'},
    'output': None,
    'repo': 'mi-pyt-label-robot/r1',
    'token': 'XXXXXXXXXX'}
