import requests
import click
import configparser
import os
import time
import re
from flask import Flask
from flask import render_template
from flask import request as flask_request

g_args = None
app = Flask(__name__)

"""
    GitHub issue ROBOT

    Tomas Kvasnicka @ FIT CTU 2016 for MI-PYT
    kvasntom@fit.cvut.cz

    GitHub Robot Account
    default user: gh_issue_agent-label-robot
    pass: see auth.cfg

    - requirements: https://edux.fit.cvut.cz/courses/MI-PYT/tutorials/01_requests_click
    - additional functionality:
        - use conditional HTTP requests where possible
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


def download_comments(comments_url, request, args):
    ret = []

    response = requests.get(comments_url, headers=request['headers'])
    if 'link' in response.headers:
        links = response.headers['link'].split(',')
        links = {x.split("rel=")[1].strip('"'): x.split(';')[0].strip('<').strip('>') for x in links}

        if 'next' in links:
            ret += download_comments(links['next'], request, args)

    for comment in response.json():
        ret += [comment['body']]

    return ret


def process_response(response, request, labels, args):
    """ process github API response with issues """

    ret = []

    if 'link' in response.headers:
        links = response.headers['link'].split(',')
        links = {x.split("rel=")[1].strip('"'): x.split(';')[0].strip('<').strip('>') for x in links}

        if 'next' in links:
            r = requests.get(links['next'], headers=request['headers'])
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
            r = requests.patch(request['api'] + args['repo'] + '/issues/' +
                               str(issue['number']), json=issue, headers=request['headers'])

            if r.status_code != 200:
                print("Editing labels failed:", str(r.status_code), '/', str(r.json()), file=args['output'])
                ret += [(False, response, r)]
            else:
                print("Patched issue", str(issue['number']), "-", issue['title'], "with labels:",
                      str(issue['labels']), file=args['output'])
                ret += [(True, response, r)]

    return ret


def parse_file(file):
    """ parse config file """

    if not os.path.isfile(file):
        raise FileNotFoundError("File " + str(file) + " doesn't exist")

    config = configparser.ConfigParser()
    config.read(file)

    return config  # return ConfigParser() object


def web_main(args):
    global g_args
    g_args = args
    app.run()


def console_main(args):
    """ get issues from github and label them """

    ret = []
    api = 'https://api.github.com/repos/'
    regexp = {re.compile(r, re.IGNORECASE): v for r, v in args['labels'].items()}
    headers = {'Authorization': 'token ' + args['token'], 'User-Agent': 'label-robot'}

    i = 0  # FIXME: Change to 'while True' if script is supposed to run forever
    while i < 3:
        i += 1

        # When using requests.Session() GH sometimes returns something wrong, requests are unable to handle it and
        # requests.exceptions.ConnectionError: ('Connection aborted.', BadStatusLine("''",)) is raised.
        #
        # See http://stackoverflow.com/questions/25326616/unexpected-keyword-argument-buffering-python-client
        # and http://stackoverflow.com/questions/26435831/getting-strange-connection-aborted-errors-with-python-requests
        # and http://stackoverflow.com/questions/30192033/python-script-stops-responding-after-a-while
        # and appropriate issues on github page of requests module. Not going to solve this now. Conditionals anyway.
        response = requests.get(api + args['repo'] + '/issues', headers=headers)

        if response.status_code != 304:
            headers['If-None-Match'] = response.headers['etag'] if 'etag' in response.headers else None

            if response.status_code == 200:
                request = {'api': api, 'headers': headers}
                ret += process_response(response, request, regexp, args)
            else:
                print('Fetching issues for', args['repo'], 'failed:', str(response.status_code), '/', response.text,
                      file=args['output'])
        else:
            print("GitHub output unchanged, no action needed", file=args['output'])

        time.sleep(args['interval'])

    # from pprint import pprint as pp
    # pp(ret)


def parse_args(repo, auth_file, label_file, interval, default_label, comments, output):
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
            'interval': interval,
            'default_label': default_label,
            'comments': comments,
            'output': output}


@click.group()
def cli():
    pass


@cli.command()
@click.option('--repo', default='gh_issue_agent-label-robot/r1', help='default repo to watch, including username')
@click.option('--auth-file', default='auth.cfg', help='path to auth file')
@click.option('--label-file', default='labels.cfg', help='path to label definitions file')
@click.option('--interval', default=10, help='how often to check for issues; in sec')
@click.option('--default-label', default='take-a-look-personally', help='default label')
@click.option('--comments', default=True, help='check comments')
@click.option('--output', default=None, help='path to file used instead of stdout')
def web(repo, auth_file, label_file, interval, default_label, comments, output):
    return web_main(parse_args(repo, auth_file, label_file, interval, default_label, comments, output))


@cli.command()
@click.option('--repo', default='gh_issue_agent-label-robot/r1', help='default repo to watch, including username')
@click.option('--auth-file', default='auth.cfg', help='path to auth file')
@click.option('--label-file', default='labels.cfg', help='path to label definitions file')
@click.option('--interval', default=10, help='how often to check for issues; in sec')
@click.option('--default-label', default='take-a-look-personally', help='default label')
@click.option('--comments', default=True, help='check comments')
@click.option('--output', default=None, help='path to file used instead of stdout')
def console(repo, auth_file, label_file, interval, default_label, comments, output):
    return console_main(parse_args(repo, auth_file, label_file, interval, default_label, comments, output))


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/hook', methods=['POST'])
def hook():
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


def main():
    cli()