import requests
import click
import configparser
import os
import re
from flask import Flask
from flask import render_template
from flask import request as flask_request

g_args = None
app = Flask(__name__)

"""
    .. moduleauthor:: Tomas Kvasnicka <kvasntom@fit.cvut.cz>
    :synopsis: Process GitHub issues and label them based on user-defined rules

    GitHub Robot Account
    default user: mi-pyt-label-robot
    pass: see auth.cfg

    - requirements: https://edux.fit.cvut.cz/courses/MI-PYT/tutorials
    - additional functionality:
        - follow Link headers if pagination is applied
        - logfile output
        - check repository existence (NOT IMPLEMENTED YET)
        - list issues for all repositories if none was given (NOT IMPLEMENTED YET)
    - not catching python exceptions while eg. opening files -> if such things fail my superb error msg won't save it
    - in the label file do not use RE that interfere with what configparser.ConfigParser() is expecting
        - I guess '[' and ']' might hurt it
    - already labeled issues do not get checked again
        - speeds up the process in case of large number of issues
        - comments added after issue has been labeled are excluded from checking
"""


def download_comments(comments_url: str, request: dict, args: dict) -> list:
    """

    Recursively download comments from a given GitHub URL

    :param comments_url: GitHub URL containing comments
    :param request: HTTP request parameters (headers, token, etc)
    :param args: arguments passed on the command line + session
    :return: list of strings containing comments

    Using data in request connect and session in args['session'] connect to comments_url and download its content. Based
    on GH documentation the content is a JSON which will be processed and the text of each comment will be saved to ret.

    If there is 'Link' HTTP header containing the word 'next' then recursively follow the URL associated with the header
    and use this URL as new comments_url.
    """

    ret = []

    response = args['session'].get(comments_url, headers=request['headers'])
    if 'link' in response.headers:
        links = response.headers['link'].split(',')
        links = {x.split("rel=")[1].strip('"'): x.split(';')[0].strip('<').strip('>') for x in links}

        if 'next' in links:
            ret += download_comments(links['next'], request, args)

    for comment in response.json():
        ret += [comment['body']]

    return ret


def process_response(response: requests.Response, request: dict, labels: dict, args: dict) -> list:
    """

    Recursively process JSON response from GitHub API containing data about issues

    :param response: HTTP response parameters (headers, body, etc)
    :param request: HTTP request parameters (headers, token, etc)
    :param labels: regular expressions and labels corresponding with these expressions
    :param args:  arguments passed on the command line + session
    :return: list of tuples

    Using data in response.json() iterate over issues and search its titles and bodies for regular expressions given by
    labels. When such RE is found set a label for given issue accordingly to labels. Send a PATCH HTTP request back to
    GitHub API to update the issue with associated labels.
    """

    ret = []

    if 'link' in response.headers:
        links = response.headers['link'].split(',')
        links = {x.split("rel=")[1].strip('"'): x.split(';')[0].strip('<').strip('>') for x in links}

        if 'next' in links:
            r = args['session'].get(links['next'], headers=request['headers'])
            ret += process_response(r, request, labels, args)

    for issue in response.json():
        if not issue['labels']:
            issue['labels'] = [label for regexp, label in labels.items()
                               if re.search(regexp, issue['title']) or re.search(regexp, issue['body'])]

            if args['comments']:
                comments = download_comments(issue['comments_url'], request, args)

                if comments:
                    issue['labels'] += [label for comment in comments for regexp, label in labels.items()
                                        if re.search(regexp, comment)]

            if not issue['labels']:
                issue['labels'] = [args['default_label']]

            del issue['assignee']  # GH APIv3 requires this
            r = args['session'].patch(request['api'] + args['repo'] + '/issues/' +
                                      str(issue['number']), json=issue, headers=request['headers'])

            if r.status_code != 200:
                print("Editing labels failed:", str(r.status_code), '/', str(r.json()), file=args['output'])
                ret += [(False, response, r)]
            else:
                print("Patched issue", str(issue['number']), "-", issue['title'], "with labels:",
                      str(issue['labels']), file=args['output'])
                ret += [(True, response, r)]

    return ret


def parse_file(file: str) -> dict:
    """

    Parse configuration file

    :param file: path to configuration file
    :return: parsed configuration file

    Test if given path is really a file and if yes try to parse it using standard configparser module. For information
    about the format of the file please refer to https://docs.python.org/3/library/configparser.html
    """

    if not os.path.isfile(file):
        raise FileNotFoundError("File " + str(file) + " doesn't exist")

    config = configparser.ConfigParser()
    config.read(file)

    return {s: dict(config.items(s)) for s in config.sections()}


def web_main(args: dict) -> None:
    """

    Run web server Flask

    :param args: parsed command line arguments
    :return: this function does not return

    This just starts Flask and then keeps it running. Flask's power is in its hooks. See below for a few examples.
    """

    global g_args
    g_args = args
    app.run()


def console_main(args: dict) -> int:
    """

    Go through all issues for a given GitHub repo and label them according to user-defined rules

    :param args: parsed command line arguments
    :return: 0 if everything was OK, 1 otherwise

    Connect to GitHub, get a list of issues and process this list. Very straightforward. Then just check the results of
    the processing and exit. Also, if fetching the issues failed print a error message about it and die.
    """

    ret = []
    api = 'https://api.github.com/repos/'
    regexp = {re.compile(r, re.IGNORECASE): v for r, v in args['labels'].items()}
    headers = {'Authorization': 'token ' + args['token'], 'User-Agent': 'label-robot'}

    if 'session' not in args:
        args['session'] = requests.session()

    response = args['session'].get(api + args['repo'] + '/issues', headers=headers)

    if response.status_code == 200:
        request = {'api': api, 'headers': headers}
        ret += process_response(response, request, regexp, args)
    else:
        print('Fetching issues for', args['repo'], 'failed:', str(response.status_code), '/', response.text,
              file=args['output'])
        return 1

    for r in ret:
        if not r[0]:
            return 1

    return 0


def parse_args(repo: str, auth_file: str, label_file: str, default_label: str, comments: bool, output: str) -> dict:
    """

    Parse command line arguments

    :param repo: github username and repository to use
    :param auth_file: config file containing github token for user
    :param label_file: config file containing RE expressions and labels
    :param default_label: default issue label when non from label_file matches
    :param comments: search for RE also in comments
    :param output: path to output file or None for stdout
    :return: dictionary with parsed arguments

    Use Click and parse command line arguments. Also do some basic checks like presence of the section github/labels in
    configuration files.
    """
    auth = parse_file(auth_file)

    if 'github' not in auth or 'token' not in auth['github']:
        raise SyntaxError("Your file with github token should look like this\n\n"
                          "[github]\n"
                          "token = XXXXXXXXXXXXXX\n\n"
                          "Obviously 'XXXXXXXXXXXXXX' is replaced with your secret token")

    labels = parse_file(label_file)
    if 'labels' not in labels:
        raise SyntaxError("Your file with label definitions should look like this\n\n"
                          "[labels]\n"
                          ".*serious.* = serious_issue\n"
                          ".*bug.* = possible_bug\n"
                          "....\n\n"
                          "Obviously label definitions should use basic RE and are totally up to you")

    if output:
        output = open(output, 'a')

    return {'token': auth['github']['token'],
            'labels': labels['labels'],
            'repo': repo,
            'default_label': default_label,
            'comments': comments,
            'output': output}


@click.group()
def cli():
    """
    Please see Click documentation - http://click.pocoo.org/5/
    :return: None
    """
    pass


@cli.command()
@click.option('--repo', default='mi-pyt-label-robot/r1', help='default repo to watch, including username')
@click.option('--auth-file', default='auth.cfg', help='path to auth file')
@click.option('--label-file', default='labels.cfg', help='path to label definitions file')
@click.option('--default-label', default='take-a-look-personally', help='default label')
@click.option('--comments', default=True, help='check comments')
@click.option('--output', default=None, help='path to file used instead of stdout')
def web(repo: str, auth_file: str, label_file: str, default_label: str, comments: bool, output: str) -> None:
    """

    Run web_main with parsed command line arguments

    :param repo: see parse_args
    :param auth_file: see parse_args
    :param label_file: see parse_args
    :param default_label: see parse_args
    :param comments: see parse_args
    :param output: see parse_args
    :return: return code from web_main

    For the description of Click's command please see Click documentation - http://click.pocoo.org/5/
    """
    return web_main(parse_args(repo, auth_file, label_file, default_label, comments, output))


@cli.command()
@click.option('--repo', default='mi-pyt-label-robot/r1', help='default repo to watch, including username')
@click.option('--auth-file', default='auth.cfg', help='path to auth file')
@click.option('--label-file', default='labels.cfg', help='path to label definitions file')
@click.option('--default-label', default='take-a-look-personally', help='default label')
@click.option('--comments', default=True, help='check comments')
@click.option('--output', default=None, help='path to file used instead of stdout')
def console(repo: str, auth_file: str, label_file: str, default_label: str, comments: bool, output: str) -> int:
    """

    Run console_main with parsed command line arguments

    :param repo: see parse_args
    :param auth_file: see parse_args
    :param label_file: see parse_args
    :param default_label: see parse_args
    :param comments: see parse_args
    :param output: see parse_args
    :return: return code from console_main

    For the description of Click's command please see Click documentation - http://click.pocoo.org/5/
    """
    return console_main(parse_args(repo, auth_file, label_file, default_label, comments, output))


@app.route('/')
def index():
    """

    Flask hook for path '/'

    :return: whatever Flask.render_template returns

    This functions gets called every time a HTTP request like this 'http://localhost' is made. It's the default location
    for requests with no precise location. Currently this calls Flask's function render_template and returns a web page
    based on gh_issue_agent/templates/index.html.

    For Flask documentation please see http://flask.pocoo.org/docs/0.11/
    """
    return render_template('index.html')


@app.route('/hook', methods=['POST'])
def hook() -> str:
    """

    Process incoming issue and label it accordingly

    :return: empty string

    When a POST request with '/hook' in its location is received then its body is passed to this function. It parses the
    body as a JSON and tries to label issues in a similar manner as process_response -> search issue title and body for
    for string matching one of configured RE and set a label configured for this RE.

    It is meant to be used with GitHub webhooks - when the issue gets created a request is sent to this '/hook' location
    and this code labels the issue immediately. Event-driven issue labeling ;)
    """
    if not g_args:
        token = parse_file('auth.cfg')['github']['token']
        labels = parse_file('labels.cfg')['labels']
        labels = {re.compile(r, re.IGNORECASE): v for r, v in labels.items()}
    else:
        token = g_args['token']
        labels = {re.compile(r, re.IGNORECASE): v for r, v in g_args['labels'].items()}

    issue = flask_request.get_json()
    api = 'https://api.github.com/repos/'
    headers = {'Authorization': 'token ' + token, 'User-Agent': 'webhook-gh'}

    if not issue['issue']['labels']:
        issue['issue']['labels'] = [label for regexp, label in labels.items()
                                    if re.search(regexp, issue['issue']['title']) or
                                    re.search(regexp, issue['issue']['body'])]

        if not issue['issue']['labels']:
            issue['issue']['labels'] = ['take-a-look-personally']

        del issue['issue']['assignee']
        if g_args is None:
            r = requests.patch(api + 'gh_issue_agent-label-robot/' + issue['repository']['name'] + '/issues/' +
                               str(issue['issue']['number']), json=issue['issue'], headers=headers)
        else:
            r = requests.patch(api + g_args['repo'] + '/issues/' +
                               str(issue['issue']['number']), json=issue['issue'], headers=headers)

        if r.status_code != 200:
            print("Editing labels failed:", str(r.status_code), '/', str(r.json()))

    return ''


def main() -> None:
    """

    Wrapper for cli() function for __main__.py

    :return: None

    See python packaging details for more info on __main__.py && __init__.py usage
    """
    cli()
