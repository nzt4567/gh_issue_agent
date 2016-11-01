import pytest
import gh_issue_agent as gh
import io
import configparser


@pytest.mark.parametrize(['repo', 'auth_file', 'label_file', 'interval', 'default_label', 'comments', 'output'],
                         [('gh_issue_agent-label-robot/r1',
                           'auth.cfg',
                           'labels.cfg',
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
    if auth_file == 'auth.cfg' and label_file == 'labels.cfg':
        args = gh.parse_args(repo, auth_file, label_file, interval, default_label, comments, output)
        assert type(args['token']) == str and args['token'] != ''
        assert type(args['labels']) == configparser.SectionProxy and args['labels']
        assert args['repo'] == repo
        assert args['interval'] == interval
        assert args['default_label'] == default_label
        assert args['comments'] == comments
        assert not args['output'] or type(args['output']) == io.TextIOWrapper
    else:
        with pytest.raises(FileNotFoundError):
            gh.parse_args(repo, auth_file, label_file, interval, default_label, comments, output)
