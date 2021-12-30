# Django Fett

Django Fett is an incomplete code generator used on several projects. 
This is an attempt to clean it up and make it public for consumption.

Django Fett is different because it leverages Frontmatter Metadata and exposes the extra metadata into the template context.
Frontmatter Metadata may also contain variables that make setting an output filename cleaner than trying to save file or folder names with Jinja syntax.

## TODO: Quick start

## Templates

A Fett template is a header of a markdown-like frontmatter and a body of an Jinja2 templating engine.

```markdown
---                               <---- frontmatter section
filename: app/{{ __model__.meta_model_name }}.py
---

from django.contrib import admin  <---- body, Jinja

class {{ __model__.name }}Admin(admin.ModelAdmin):
    pass

```

## Predefined Variables

| Variable | Content | Example | 
| ---- | ---- | ---- |
| `__app__` | |
| `__metadata__` | | 
| `__model__` | | 

## Example Usage

### Example Template (`./_templates/list_models.html`)

```html
---
filename: output/{{ __model__.meta_model_name }}.py
---

# App: {{ __app__.name }}

## Fields
{% for field in __model__.get_fields() %}
- {{ field }}{% endfor %}

## Metadata
{{ __metadata__ }}

```

This example assumes we have a model in `app/models.py` which contains a model named `Backup`.

```shell
python src/fett.py --app-name=app --input=./_templates/list_models.html
```

This will create a file for every model in our `models.py` file.
For our `Backup` model, the file will be rendered and saved as `output/backup.py`.

```
# App: app

## Fields

- app.Backup.id
- app.Backup.server
- app.Backup.backup_configuration
- app.Backup.status
- app.Backup.restore_status
- app.Backup.archive_path
- app.Backup.size
- app.Backup.uuid
- app.Backup.duration
- app.Backup.last_backup_time

## Metadata
{'filename': 'output/backup.py'}
```

## TODO: Tests...
