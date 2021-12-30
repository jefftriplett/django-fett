# Please see: https://github.com/jefftriplett/scripts-to-rule-them-all

set dotenv-load := false

@_default:
    just --list

# installs/updates all dependencies
@bootstrap:
    echo "TODO: bootstrap"

# invoked by continuous integration servers to run tests
@cibuild:
    echo "TODO: cibuild"

# opens a console
@console:
    echo "TODO: console"

# starts app
@server:
    echo "TODO: server"

# sets up a project to be used for the first time
@setup:
    echo "TODO: setup"

# runs tests
@test:
    echo "TODO: test"

# updates a project to run at its current version
@update:
    pip install -U pip
    rm -f requirements.txt
    pip install -U -r requirements.in
    pip-compile requirements.in
