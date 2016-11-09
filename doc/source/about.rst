About
=====

gh_issue_agent is a simple python application that helps you manage your GitHub issues. It is able to connect to your
GitHub account, parse all issues for a given repository and label them based on user-defined rules. You may run it as
a script (manually or using eg. cron) or as a standalone web server. Please see :ref:`installation` for install and usage
instructions.



Web server usage
================

When used as a web server you need to setup GitHub webhook first. For more information regarding web-server usage please
see https://developer.github.com/webhooks/ and :ref:`installation`.



Console usage
=============

When used from console the application is fairly straightforward. It accepts numerous command line arguments that are
explained when the application is launched without any arguments.