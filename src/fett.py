import django
import frontmatter
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
    def name(self):
        return self.model._meta.object_name

    @property
    def snake_case_name(self):
        return camel_case_to_spaces(self.name).replace(" ", "_")

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
    app_name: Optional[str] = "app",  # TODO: clean this up...
    include_hidden: Optional[bool] = False,
    include_parents: Optional[bool] = True,
    input_filename: str = typer.Option("input"),
    overwrite: Optional[bool] = False,
):

    get_app = apps.get_app_config
    # get_models = AppConfig.get_models

    app = get_app(app_name)

    models = Models(app=app)

    for model in models:
        with Path(input_filename).open() as input_buffer:
            print(
                f"processing [italic]{inflection.underscore(model.name)}[/italic] model..."
            )

            # first pass:
            # - process source with jinja2
            # - read frontmatter
            source_contents = input_buffer.read()
            template = Template(source_contents)
            context = {
                "__app__": app,
                "__model__": model,
            }
            output = template.render(context)
            post = frontmatter.loads(output)

            # second pass:
            # - extra metadata from frontmatter
            # - process source with jinja2 using metadata
            metadata = post.metadata
            template = Template(source_contents)

            context["__metadata__"] = metadata

            output = template.render(context)
            post = frontmatter.loads(output)

            assert "filename" in post

            output_path = Path(post["filename"])
            if not output_path.parent.exists():
                output_path.parent.mkdir(parents=True)

            output_path.write_text(post.content)


if __name__ == "__main__":
    typer.run(main)
