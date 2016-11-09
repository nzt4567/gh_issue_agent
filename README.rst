mi-pyt
======

Created for the MI-PYT course @ FIT CTU

This project currently implements a GitHub-Issue-Labeling-Robot.
It means that it connects to GH, searches issues and labels them based
on given config. And it has a package on testing PyPI.

Install using `python3 -m pip install --extra-index-url https://testpypi.python.org/pypi gh_issue_agent`
To run the tests simply run `python3 setup.py test`. Normally a recorded betamax cassete will be used, but if you want
to re-record it using your own github account set the AUTH_FILE='/path/to/config/file.cfg' ENV. Aslo, you will actually
have to change the code of the tests, as they cannot currently accept parameters from the command line (not even sure
this is possible) and therefore you need to change `repo` path.

To build the documentation use `make html` inside of the `doc` directory. To run doctests simply run `make doctest` in
the same directory. Also, you need to have package `sphinx` installed.