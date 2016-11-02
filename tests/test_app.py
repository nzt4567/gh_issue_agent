import pytest
import gh_issue_agent as gh
import io
import configparser
from flexmock import flexmock
import os


@pytest.mark.parametrize(['repo', 'auth_file', 'label_file', 'interval', 'default_label', 'comments', 'output'],
                         [('gh_issue_agent-label-robot/r1',
                           'imaginary_auth.cfg',
                           'imaginary_labels.cfg',
                           10,
                           'take-a-look-personally',
                           True,
                           None),
                          ('another/repo',
                           '/non-existing-file',
                           '/another-one',
                           10,
                           'asdfg',
                           False,
                           '/dev/null')])
def test_args(repo, auth_file, label_file, interval, default_label, comments, output):
    if auth_file == 'imaginary_auth.cfg' and label_file == 'imaginary_labels.cfg':
        mock = flexmock(os.path)
        mock.should_call('isfile')
        mock.should_receive('isfile').with_args(auth_file).and_return(True)
        mock.should_receive('isfile').with_args(label_file).and_return(True)

        mock = flexmock(configparser.ConfigParser)
        mock.should_call('sections')
        mock.should_receive('sections').and_return(['github', 'labels'])
        mock.should_call('items')
        mock.should_receive('items').with_args('github').and_return({'token': 'XXXXXXXXXX'})
        mock.should_receive('items').with_args('labels').and_return({'.*bug.*': 'possible_bug', '.*now.*': 'ASAP'})

        args = gh.parse_args(repo, auth_file, label_file, interval, default_label, comments, output)

        assert type(args['token']) == str and args['token'] != ''
        assert type(args['labels']) == dict and args['labels']
        assert args['repo'] == repo
        assert args['interval'] == interval
        assert args['default_label'] == default_label
        assert args['comments'] == comments
        assert not args['output'] or type(args['output']) == io.TextIOWrapper
    else:
        with pytest.raises(FileNotFoundError):
            gh.parse_args(repo, auth_file, label_file, interval, default_label, comments, output)


@pytest.fixture
def flask_app():
    gh.app.config['TESTING'] = True
    return gh.app.test_client()


def test_web(flask_app):
    assert 'Usage of this web server is very easy.' in flask_app.get('/').data.decode('utf-8')
