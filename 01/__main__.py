import requests
import click
import configparser
import os
import time
import re

"""
    GitHub issue ROBOT

    Tomas Kvasnicka @ FIT CTU 2016 for MI-PYT
    kvasntom@fit.cvut.cz

    GitHub Robot Account
    user: mi-pyt-label-robot
    pass: see auth.cfg

    - requirements: https://edux.fit.cvut.cz/courses/MI-PYT/tutorials/01_requests_click
    - additional functionality:
        - use conditional HTTP requests where possible
        - follow Link headers if pagination is applied (IN PROGRESS)
        - logfile output
        - check repository existence (NOT IMPLEMENTED YET)
        - list issues for all repositories if none was given (NOT IMPLEMENTED YET)
    - not catching python exceptions while eg. opening files -> if such things fail my superb error msg won't save it
    - in the label file do not use RE that interfere with what configparser.ConfigParser() is expecting
        - I guess '[' and ']' might hurt it
"""


def process_response(response, request, labels, output, link):
    """ process github API response with issues """

    # TODO: Handle Link header
    for issue in response.json():
        if not issue['labels']:
            issue['labels'] = [label for regexp, label in labels.items()
                               if re.search(regexp, issue['title']) or re.search(regexp, issue['body'])]

            if issue['labels']:
                del issue['assignee']  # GH APIv3 requires this
                r = requests.patch(request['api'] + request['user'] + '/' + request['repo'] + '/issues/' +
                                   str(issue['number']), json=issue, headers=request['headers'])

                if r.status_code != 200:
                    print("Editing labels failed:", str(r.status_code), '/', str(r.json()), file=output)
                else:
                    print("Patched issue", str(issue['number']), "-", issue['title'], "with labels:",
                          str(issue['labels']), file=output)


def parse_file(file):
    """ parse config file """

    if not os.path.isfile(file):
        raise FileNotFoundError("File " + str(file) + " doesn't exist")

    config = configparser.ConfigParser()
    config.read(file)

    return config  # return ConfigParser() object


def main(args):
    """ get issues from github and label them """

    user = 'mi-pyt-label-robot'
    api = 'https://api.github.com/repos/'
    regexp = {re.compile(r, re.IGNORECASE): v for r, v in args['labels'].items()}
    headers = {'Authorization': 'token ' + args['token'], 'User-Agent': user}

    i = 0  # FIXME: Change to 'while True' if script is supposed to run for ever
    while i < 3:
        i += 1

        # When using requests.Session() GH sometimes returns something wrong, requests cannot handle it and
        # requests.exceptions.ConnectionError: ('Connection aborted.', BadStatusLine("''",)) is raised.
        #
        # See http://stackoverflow.com/questions/25326616/unexpected-keyword-argument-buffering-python-client
        # and http://stackoverflow.com/questions/26435831/getting-strange-connection-aborted-errors-with-python-requests
        # and http://stackoverflow.com/questions/30192033/python-script-stops-responding-after-a-while
        # and appropriate issues on github page of requests module. Not going to solve this now. Conditionals anyway.
        response = requests.get(api + user + '/' + args['repo'] + '/issues', headers=headers)

        if response.status_code != 304:
            headers['If-None-Match'] = response.headers['etag']  # if 'etag' in response.headers else None

            if response.status_code == 200:
                request = {'api': api, 'user': user, 'repo': args['repo'], 'headers': headers}
                process_response(response, request, regexp, args['output'], 'link' in response.headers)
            else:
                print('Fetching issues for', args['repo'], 'failed:', str(response.status_code), '/', response.text,
                      file=args['output'])

        time.sleep(args['interval'])


@click.command()
@click.option('--repo', default='r1', help='default repo to watch')
@click.option('--auth-file', default='auth.cfg', help='path to auth file')
@click.option('--label-file', default='labels.cfg', help='path to label definitions file')
@click.option('--interval', default=10, help='how often to check for issues; in sec')
@click.option('--default-label', default='take-a-look-personally', help='default label')
@click.option('--comments', default=False, help='check comments')
@click.option('--output', default=None, help='path to file used instead of stdout')
def parse_args(repo, auth_file, label_file, interval, default_label, comments, output):
    """ parse command line arguments """

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

    return main({'token': auth['github']['token'],
                 'labels': labels['labels'],
                 'repo': repo,
                 'interval': interval,
                 'default_label': default_label,
                 'comments': comments,
                 'output': output})


if __name__ == '__main__':
    parse_args()