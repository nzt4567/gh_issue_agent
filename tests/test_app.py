import pytest
import gh_issue_agent as gh
import io
import configparser
from flexmock import flexmock
import os
import betamax

with betamax.Betamax.configure() as config:
    config.cassette_library_dir = 'tests/cassetes'
    if 'AUTH_FILE' in os.environ:
        auth_config = configparser.ConfigParser()
        auth_config.read(os.environ['AUTH_FILE'])

        auth = {s: dict(auth_config.items(s)) for s in auth_config.sections()}
        token = auth['github']['token']
        config.default_cassette_options['record_mode'] = 'all'
    else:
        token = 'XXXXXXXX'
        config.default_cassette_options['record_mode'] = 'none'

    config.define_cassette_placeholder('<TOKEN>', token)


@pytest.mark.parametrize(['repo', 'auth_file', 'label_file', 'default_label', 'comments', 'output'],
                         [('mi-pyt-label-robot/r1',
                           'imaginary_auth.cfg',
                           'imaginary_labels.cfg',
                           'take-a-look-personally',
                           True,
                           None),
                          ('another/repo',
                           '/non-existing-file',
                           '/another-one',
                           'asdfg',
                           False,
                           '/dev/null')])
def test_args(repo, auth_file, label_file, default_label, comments, output):
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

        args = gh.parse_args(repo, auth_file, label_file, default_label, comments, output)

        assert type(args['token']) == str and args['token'] != ''
        assert type(args['labels']) == dict and args['labels']
        assert args['repo'] == repo
        assert args['default_label'] == default_label
        assert args['comments'] == comments
        assert not args['output'] or type(args['output']) == io.TextIOWrapper
    else:
        with pytest.raises(FileNotFoundError):
            gh.parse_args(repo, auth_file, label_file, default_label, comments, output)


@pytest.fixture
def flask_app():
    gh.app.config['TESTING'] = True
    return gh.app.test_client()


def test_web(flask_app):
    assert 'Usage of this web server is very easy.' in flask_app.get('/').data.decode('utf-8')


def test_console(betamax_session):
    args = {'token': token, 'labels': {'.*bug.*': 'possible_bug', '.*now.*': 'ASAP'}, 'repo': 'mi-pyt-label-robot/r1',
            'default_label': 'default-test-label', 'comments': False, 'output': None,
            'session': betamax_session}

    assert gh.console_main(args) == 0
