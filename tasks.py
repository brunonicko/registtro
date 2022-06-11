import sys

from invoke import task  # type: ignore


if sys.version_info[0:2] < (3, 10):
    sys.stderr.write(f"Python 3.10+ is required for development tasks, you are running {sys.version}\n")
    sys.exit(1)


@task
def docs(c):
    c.run("sphinx-build -M html ./docs/source ./docs/build")


@task
def tests(c):
    c.run("python -m pytest -vv -rs tests")
    c.run("python -m pytest --doctest-modules -vv -rs README.rst")


@task
def tox(c):
    c.run("tox")


@task
def mypy(c):
    c.run("mypy registtro.py")


@task
def lint(c):
    c.run("flake8 registtro.py --count --select=E9,F63,F7,F82 --show-source --statistics")
    c.run("flake8 tests_registtro.py --count --select=E9,F63,F7,F82 --show-source --statistics")
    c.run(
        "flake8 registtro.py --count --ignore=F403,F401,E203,E731,C901,W503 "
        "--max-line-length=120 --statistics"
    )
    c.run(
        "flake8 tests_registtro.py --count --ignore=F403,F401,E203,E731,C901,W503 "
        "--max-line-length=120 --statistics"
    )


@task
def black(c):
    c.run("black registtro.py --line-length=120")
    c.run("black tests_registtro.py --line-length=120")


@task
def checks(c):
    black(c)
    lint(c)
    mypy(c)
    tox(c)
