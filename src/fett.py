import django
import frontmatter
import gzip
import inflection
import os
import sys
import typer

from django.apps import apps
from django.contrib.postgres.fields import ArrayField
from django.db.models import ForeignKey
from django.db.models import JSONField
from django.db.models import OneToOneField
from django.db.models.fields import AutoField
from django.db.models.fields import BooleanField
from django.db.models.fields import CharField
from django.db.models.fields import DateField
from django.db.models.fields import DateTimeField
from django.db.models.fields import DecimalField
from django.db.models.fields import IntegerField
from django.db.models.fields import SmallIntegerField
from django.db.models.fields import TextField
from django.utils.text import camel_case_to_spaces

# from django.db.models.fields import UUIDField
# from django_postgres_unlimited_varchar import UnlimitedCharField
from jinja2 import Template
from pathlib import Path
from rich import print
from typing import Optional
from urllib.parse import urlparse
from urllib.request import urlopen


# bootstrap Django
# TODO: clean this up
sys.path.append(".")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()


try:
    from django.db.models.loading import get_models

except ImportError:

    def get_models(app):
        yield from app.get_models()


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
    IntegerField,
    SmallIntegerField,
)
STRING_FIELDS = (
    CharField,
    TextField,
    # UnlimitedCharField,
)


def get_field_names(fields):
    return [x.name for x in fields]


class App:
    def __init__(self, *, app):
        self.app = app
        self.models = Models(app=app)

    @property
    def name(self):
        return self.app.name


class Field:
    def __init__(self, field):
        self.field = field


class Fields(list):
    def __init__(self, model):
        super().__init__()
        self.model = model
        self.extend([Field(field=field) for field in self.model._meta.concrete_fields])


class Model:
    def __init__(self, *, model: str):
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
    def local_field_names(self):
        return get_field_names(self.model._meta.local_fields)

    @property
    def meta_db_table(self):
        return self.model._meta.db_table

    @property
    def meta_model_name(self):
        return self.model._meta.model_name

    @property
    def meta_verbose_name(self):
        return self.model._meta.verbose_name

    @property
    def meta_verbose_name_plural(self):
        return self.model._meta.verbose_name_plural

    @property
    def meta_object_name(self):
        return self.model._meta.object_name

    @property
    def name(self):
        # TODO: same as `meta_object_name`
        return self.model._meta.object_name

    @property
    def snake_case_name(self):
        return camel_case_to_spaces(self.model._meta.object_name).replace(" ", "_")

    @property
    def snake_case_name_plural(self):
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
    def tableize(self):
        return inflection.tableize(self.meta_verbose_name)

    @property
    def underscore(self):
        return inflection.underscore(self.meta_verbose_name.replace(" ", ""))

    @property
    def underscore_plural(self):
        return inflection.underscore(self.meta_verbose_name_plural.replace(" ", ""))


class Models(list):
    def __init__(self, *, app: str):
        super().__init__()
        self.app = app
        self.extend([Model(model=model) for model in get_models(self.app)])


def main(
    app_name: str = "app",  # TODO: clean this up...
    input_filename: Path = typer.Option(
        "input",
        "--input",
        allow_dash=True,
        dir_okay=True,
        file_okay=True,
        readable=True,
        resolve_path=True,
        writable=False,
    ),
    overwrite: Optional[bool] = False,
):

    get_app = apps.get_app_config
    # get_models = AppConfig.get_models

    app = get_app(app_name)
    app = App(app=app)

    if input_filename is None:
        source_contents = None
        raise typer.Abort()

    elif input_filename.exists():
        if input_filename.is_file():
            source_contents = input_filename.read_text()

        elif input_filename.is_dir():
            source_contents = None
            raise typer.Abort()

        else:
            raise typer.Abort()

    elif str(input_filename) == "-":
        source_contents = sys.stdin.read()

    elif str(input_filename).startswith("http"):
        source_contents = None
        url = urlparse(input_filename)
        if url.scheme not in SUPPORTED_SCHEMES:
            print(f"{url.scheme} scheme is not supported")
            raise typer.Abort()

        if url.scheme in SUPPORTED_SCHEMES:
            if input_filename.endswith(".gz"):
                source_contents = gzip.GzipFile(
                    mode="r", fileobj=urlopen(input_filename)
                )

            source_contents = urlopen(input_filename)

    else:
        raise typer.Abort()

    post = frontmatter.loads(source_contents)

    has_filename = "to" in post.metadata
    has_model_in_filename = has_filename or "__model__" in post.metadata

    if has_model_in_filename:
        models = app.models
    else:
        models = [None]

    for model in models:
        if model:
            print(
                f"found [italic][yellow]{inflection.underscore(model.name)}[/yellow][/italic] model..."
            )

        # render our entire document/template with jinja2
        template = Template(source_contents)
        context = {
            "__app__": app,
            "__metadata__": None,
            "__model__": model,
        }
        output = template.render(context)

        # load our process file into Frontmatter so we can pull out the
        # post processed metadata.
        post = frontmatter.loads(output)

        # second pass:
        # - extra metadata from frontmatter
        # - process source with jinja2 using metadata
        metadata = post.metadata
        template = Template(source_contents)

        # added our parsed metadata to our complete context
        context["__metadata__"] = metadata

        output = template.render(context)
        post = frontmatter.loads(output)

        if "to" in post.metadata:
            output_path = Path(post["to"])
            if not output_path.parent.exists():
                output_path.parent.mkdir(parents=True)

            if not output_path.exists() or overwrite:
                output_path.write_text(post.content)

        else:
            print(post.content)


if __name__ == "__main__":
    typer.run(main)
