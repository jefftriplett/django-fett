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
    python src/fett.py \
        --app-name=testapp \
        --input=./_templates/admin.py \
        --overwrite

    echo

    python src/fett.py \
        --app-name=testapp \
        --input=./_templates/fixtures.py \
        --overwrite

    # python src/fett.py \
    #     --app-name=app \
    #     --input-filename=./_templates/list_models.html

# updates a project to run at its current version
@update:
    pip install --upgrade pip pip-tools
    pip install --upgrade --requirement requirements.in
    pip-compile --resolver=backtracking requirements.in
