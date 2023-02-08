import django
import frontmatter
import gzip
import inflection
import os
import requests
import sys
import typer

# from django.db.models import BinaryField
# from django.db.models import DurationField
# from django.db.models import EmailField
# from django.db.models import FileField
# from django.db.models import FloatField
# from django.db.models import GenericIPAddressField
# from django.db.models import ImageField
# from django.db.models import IPAddressField
# from django.db.models import ManyToManyField
# from django.db.models import SlugField
# from django.db.models import TimeField
# from django.db.models import URLField
# from django.db.models import UUIDField
# from django.db.models.fields import UUIDField
from django.apps import apps
from django.contrib.postgres.fields import ArrayField
from django.db.models import AutoField
from django.db.models import BigIntegerField
from django.db.models import BooleanField
from django.db.models import CharField
from django.db.models import DateField
from django.db.models import DateTimeField
from django.db.models import DecimalField
from django.db.models import ForeignKey
from django.db.models import IntegerField
from django.db.models import JSONField
from django.db.models import OneToOneField
from django.db.models import PositiveIntegerField
from django.db.models import PositiveSmallIntegerField
from django.db.models import SmallIntegerField
from django.db.models import TextField
from django.utils.text import camel_case_to_spaces

# from django_postgres_unlimited_varchar import UnlimitedCharField
from jinja2 import Template
from pathlib import Path
from rich import print
from typing import List
from typing import Optional
from urllib.parse import urlparse

# from urllib.request import urlopen


try:
    from django.db.models.loading import get_models

except ImportError:

    def get_models(app):
        yield from app.get_models()


BLOCK_END_STRING = "%}"
BLOCK_START_STRING = "{%"
COMMENT_END_STRING = "#}"
COMMENT_START_STRING = "{#"
VARIABLE_END_STRING = "}}"
VARIABLE_START_STRING = "{{"

SUPPORTED_SCHEMES = ("http", "https")

# TODO: set this via config and/or ENV
IGNORE_FIELD_NAMES = [
    "id",
]

ADMIN_FILTER_FIELDS = (BooleanField,)
BOOLEAN_FIELDS = (BooleanField,)
CHAR_FIELDS = (
    CharField,
    # UnlimitedCharField,
)
DECIMAL_FIELDS = (DecimalField,)
FILTER_FIELDS = (
    AutoField,
    CharField,
    DateField,
    IntegerField,
    # UnlimitedCharField,
)
FOREIGN_FIELDS = (
    ForeignKey,
    OneToOneField,
)
INTEGER_FIELDS = (
    BigIntegerField,
    IntegerField,
    PositiveIntegerField,
    PositiveSmallIntegerField,
    SmallIntegerField,
)
STRING_FIELDS = (
    CharField,
    TextField,
    # UnlimitedCharField,
)


class App:
    def __init__(self, *, app: object, sort_models: bool = True):
        self.app = app
        self.models = Models(app=app, sort_models=sort_models)

    @property
    def name(self) -> str:
        return self.app.name


class Field:
    def __init__(self, *, field: object):
        self.field = field


class Fields(list):
    def __init__(self, *, model: object):
        super().__init__()
        self.model = model
        self.extend([Field(field=field) for field in self.model._meta.concrete_fields])


class Model:
    def __init__(self, *, model: object):
        self.model = model

    def __str__(self):
        return self.name

    def get_fields(self, ignore_fields: bool = False):
        # return Fields(model=self.model)
        data = []
        for field in self.model._meta.concrete_fields:
            if ignore_fields:
                if field.name not in IGNORE_FIELD_NAMES:
                    data.append(field)
            else:
                data.append(field)

        return data

    @property
    def admin_filter_field_names(self):
        return get_field_names(
            filter(
                lambda x: isinstance(x, ADMIN_FILTER_FIELDS),
                self.model._meta.concrete_fields,
            )
        )

    @property
    def admin_raw_id_fields(self):
        return get_field_names(
            filter(
                lambda x: isinstance(x, FOREIGN_FIELDS),
                self.model._meta.concrete_fields,
            )
        )

    @property
    def char_field_names(self):
        return get_field_names(
            filter(
                lambda x: isinstance(x, CHAR_FIELDS), self.model._meta.concrete_fields
            )
        )

    @property
    def concrete_field_names(self):
        return get_field_names(self.model._meta.concrete_fields)

    @property
    def field_names(self):
        return get_field_names(self.model._meta.fields)

    @property
    def filter_field_names(self):
        return get_field_names(
            filter(
                lambda x: isinstance(x, FILTER_FIELDS), self.model._meta.concrete_fields
            )
        )

    @property
    def field_names_and_db_column(self):
        data = []
        for field in self.model._meta.concrete_fields:
            if field.name not in IGNORE_FIELD_NAMES:
                data.append({"name": field.name, "db_column": field.db_column})
        return data

    @property
    def field_names_and_types(self):
        data = []
        for field in self.model._meta.concrete_fields:
            if field.name not in IGNORE_FIELD_NAMES:
                is_optional = field.blank or field.null

                if isinstance(field, (ArrayField,)):
                    field_type = "list[str]"
                elif isinstance(field, BOOLEAN_FIELDS):
                    field_type = "bool"
                elif isinstance(field, (DateField,)):
                    field_type = "date"
                elif isinstance(field, (DateTimeField,)):
                    field_type = "datetime"
                elif isinstance(field, FOREIGN_FIELDS):
                    field_type = f"{field.related_model._meta.verbose_name}".replace(
                        " ", ""
                    )
                elif isinstance(field, (JSONField,)):
                    field_type = "str"
                elif isinstance(field, DECIMAL_FIELDS):
                    field_type = "Decimal"
                elif isinstance(field, INTEGER_FIELDS):
                    field_type = "int"
                elif isinstance(field, STRING_FIELDS):
                    field_type = "str"
                else:
                    field_type = "str"

                if is_optional:
                    field_type = f"Optional[{field_type}] = None"

                data.append({"name": field.name, "type": field_type})

        return data

    @property
    def foreign_field_names(self):
        return get_field_names(
            filter(
                lambda x: isinstance(x, FOREIGN_FIELDS),
                self.model._meta.concrete_fields,
            )
        )

    @property
    def local_field_names(self) -> str:
        return get_field_names(self.model._meta.local_fields)

    @property
    def meta_db_table(self) -> str:
        return self.model._meta.db_table

    @property
    def meta_model_name(self) -> str:
        return self.model._meta.model_name

    @property
    def meta_verbose_name(self) -> str:
        return self.model._meta.verbose_name

    @property
    def meta_verbose_name_plural(self) -> str:
        return self.model._meta.verbose_name_plural

    @property
    def meta_object_name(self) -> str:
        return self.model._meta.object_name

    @property
    def name(self) -> str:
        # TODO: same as `meta_object_name`
        return self.model._meta.object_name

    @property
    def snake_case_name(self) -> str:
        return camel_case_to_spaces(self.model._meta.object_name).replace(" ", "_")

    @property
    def snake_case_name_plural(self) -> str:
        return camel_case_to_spaces(self.model._meta.verbose_name_plural).replace(
            " ", "_"
        )

    @property
    def string_field_names(self):
        return get_field_names(
            filter(
                lambda x: isinstance(x, STRING_FIELDS), self.model._meta.concrete_fields
            )
        )

    @property
    def tableize(self) -> str:
        return inflection.tableize(self.meta_verbose_name)

    @property
    def underscore(self) -> str:
        return inflection.underscore(self.meta_verbose_name.replace(" ", ""))

    @property
    def underscore_plural(self) -> str:
        return inflection.underscore(self.meta_verbose_name_plural.replace(" ", ""))


class Models(list):
    def __init__(self, *, app: "App", sort_models: bool = True):
        super().__init__()
        self.app = app
        models = [Model(model=model) for model in get_models(self.app)]

        # sorts models by name
        if sort_models:
            models = [model for model in sorted(models, key=lambda k: k.name)]

        self.extend(models)


def bootstrap_django() -> None:
    sys.path.append(".")
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
    django.setup()


def get_field_names(fields):
    return [x.name for x in fields]


def open_anything(*, path: str):
    """
    Wrap path to read from paths, folders (soon), streams (via "-"),
    remote urls (https), or even gzip archived files.
    """
    if path is None:
        raise typer.Abort()

    elif Path(path).exists():
        if Path(path).is_file():
            return Path(path).read_text()

        elif Path(path).is_dir():
            raise typer.Abort()

        else:
            raise typer.Abort()

    elif str(path) == "-":
        return sys.stdin.read()

    elif str(path).startswith("http"):
        url = urlparse(path)
        if url.scheme not in SUPPORTED_SCHEMES:
            print(f"{url.scheme} scheme is not supported")
            raise typer.Abort()

        if url.scheme in SUPPORTED_SCHEMES:
            try:
                if path.endswith(".gz"):
                    response = requests.get(path)
                    response.raise_for_status()
                    return gzip.GzipFile(mode="r", fileobj=response)
                    # return gzip.GzipFile(mode="r", fileobj=urlopen(path))
                response = requests.get(path)
                response.raise_for_status()
                return response.text
            except Exception:
                raise typer.Abort()

    else:
        raise typer.Abort()


class Fett:
    def __init__(
        self,
        *,
        block_end_string: str = BLOCK_END_STRING,
        block_start_string: str = BLOCK_START_STRING,
        comment_end_string: str = COMMENT_END_STRING,
        comment_start_string: str = COMMENT_START_STRING,
        variable_end_string: str = VARIABLE_END_STRING,
        variable_start_string: str = VARIABLE_START_STRING,
    ):
        self.block_end_string = block_end_string
        self.block_start_string = block_start_string
        self.comment_end_string = comment_end_string
        self.comment_start_string = comment_start_string
        self.variable_end_string = variable_end_string
        self.variable_start_string = variable_start_string

    def get_template(self, *, source: str) -> Template:
        return Template(
            source,
            block_end_string=self.block_end_string,
            block_start_string=self.block_start_string,
            comment_end_string=self.comment_end_string,
            comment_start_string=self.comment_start_string,
            variable_end_string=self.variable_end_string,
            variable_start_string=self.variable_start_string,
            # line_comment_prefix=None,
            # line_statement_prefix=None,
        )


cli = typer.Typer()


@cli.command()
def main(
    app_name: str,
    overwrite: Optional[bool] = False,
    paths: List[Path] = typer.Option(
        None,
        "--path",
        allow_dash=True,
        dir_okay=True,
        file_okay=True,
        readable=True,
        resolve_path=True,
        writable=False,
    ),
    sort_models: Optional[bool] = True,
    stdout: Optional[bool] = False,
):
    bootstrap_django()

    get_app = apps.get_app_config
    # get_models = AppConfig.get_models

    app = get_app(app_name)
    app = App(app=app)

    fett = Fett()

    for path in paths:
        # ------------------------------------------------------------
        # Step 0
        # ------------------------------------------------------------

        source = open_anything(path=path)

        post = frontmatter.loads(source)

        _force = bool(post.metadata.get("force", False))
        _from = post.metadata.get("from", None)
        _sh = post.metadata.get("sh", None)
        _to = post.metadata.get("to", None)
        _unless_exists = bool(post.metadata.get("unless_exists", True))

        """
        see: https://www.hygen.io/docs/templates#all-frontmatter-properties
        TODO: Move into a class along with...
        - force: bool = False
        - from: str = None
        - sh: str = None
        - to: str = None
        - unless_exists: bool = True

        maybe...
        - inject
        - after
        - skip_if
        """

        has_path = "to" in post.metadata
        has_model_in_path = has_path and "__model__" in post.metadata

        if has_model_in_path:
            models = app.models
        else:
            models = [None]

        for model in models:
            if model:
                print(
                    f"found [italic][yellow]{inflection.underscore(model.name)}[/yellow][/italic] model..."
                )

            # ------------------------------------------------------------
            # Pass 1: render our entire document/template with jinja2.
            # ------------------------------------------------------------

            template = fett.get_template(source=source)
            context = {
                "__app__": app,
                "__metadata__": None,
                "__model__": model,
            }
            output = template.render(context)

            # ------------------------------------------------------------
            # Pass 2: load our process file into Frontmatter so we can
            # pull out the post processed metadata.
            # ------------------------------------------------------------

            post = frontmatter.loads(output)

            # second pass:
            # - extra metadata from frontmatter
            # - process source with jinja2 using metadata
            metadata = post.metadata

            template = fett.get_template(source=source)

            # added our parsed metadata to our complete context
            context["__metadata__"] = metadata

            output = template.render(context)

            # ------------------------------------------------------------
            # Pass 3: Output
            # ------------------------------------------------------------

            post = frontmatter.loads(output)

            if stdout:
                print(frontmatter.dumps(post))

            elif "to" in post.metadata:
                output_path = Path(post["to"])
                if not output_path.parent.exists():
                    output_path.parent.mkdir(parents=True)

                if not output_path.exists() or overwrite:
                    output_path.write_text(post.content)


if __name__ == "__main__":
    cli()
