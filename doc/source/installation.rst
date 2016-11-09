.. _installation:

Install
=======

Installation itself is done using command `python3 -m pip install --extra-index-url https://testpypi.python.org/pypi gh_issue_agent`
After installing the package you can run the command `gh_issue_agent` which is going to show some basic help. To make do
anything usable you need to setup two important things.



GitHub token
============

As an authentication method GitHub uses so called tokens. You need to obtain one. It's free no worries :) For instructions
on obtaining a token please see https://help.github.com/articles/creating-an-access-token-for-command-line-use/ and
https://github.com/settings/tokens. After you've got your token safe at home create a file that will be used for
authentication. It must contain section "github" with element "token" into which you insert your private token. Example
file might look like

[github]

token = XXXXXXXXXXXXXX

Where XXXXXXXXXXXXXX gets replaced by your token. Never ever give your token to anyone, do not upload it to public
repositories etc.



Labels configuration
====================

To make gh_issue_agent do anything useful you have to give it a database of regular expressions and matching labels.
It searches the issues (titles & body & optionally comments) for the regular expressions and in case of match it labels
the issue with given label. Again, this information is stored in a file, example file is included so please see
"labels.cfg" - it's self-explanatory.



GitHub webhooks
===============

Assuming you have already read https://developer.github.com/webhooks/ gh_issue_agent offers you a functionality to be a
GitHub webhook endpoint. That means that you launch it in it's web mode for example with a DNS name gh-agent.myweb.com
(you must own the domain myweb.com and create appropriate DNS records) and then use https://gh-agent.myweb.com/hook as
the URL in GitHub webhook setup. Then you do not have to run the script periodically but instead let the hook do the job.
Whenever an event for which your GitHub webhook is configured gets triggered you will receive a HTTP POST request.
gh_issue_agent will then process this request and automatically label the issue that triggered the event.