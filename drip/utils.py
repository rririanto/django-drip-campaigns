import sys

from django.db import models
from django.db.models import ForeignKey, OneToOneField, ManyToManyField
from django.db.models.fields.related import ForeignObjectRel as RelatedObject

# taking a nod from python-requests and skipping six
_ver = sys.version_info
is_py2 = (_ver[0] == 2)
is_py3 = (_ver[0] == 3)
basestring = None
unicode = None

if is_py2:
    basestring = basestring
    unicode = unicode
elif is_py3:
    basestring = (str, bytes)
    unicode = str


def check_redundant(model_stack, stack_limit):
    stop_recursion = False
    if len(model_stack) > stack_limit:
        # rudimentary CustomUser->User->CustomUser->User detection, or
        # stack depth shouldn't exceed x, or
        # we've hit a point where we are repeating models
        if (
            (model_stack[-3] == model_stack[-1]) or
            (len(model_stack) > 5) or
            (len(set(model_stack)) != len(model_stack))
        ):
            stop_recursion = True
    return stop_recursion


def get_field_name(field, RelatedObject):
    field_name = field.name

    if isinstance(field, RelatedObject):
        field_name = field.field.related_query_name()
    return field_name


def get_full_field(parent_field, field_name):
    if parent_field:
        full_field = "__".join([parent_field, field_name])
    else:
        full_field = field_name
    return full_field


def get_rel_model(field, RelatedObject):
    if isinstance(field, RelatedObject):
        RelModel = field.model
        # field_names.extend(get_fields(RelModel, full_field, True))
    else:
        RelModel = field.related_model
    return RelModel


def is_valid_instance(field):
    return (
        isinstance(field, ForeignKey) or
        isinstance(field, OneToOneField) or
        isinstance(field, RelatedObject) or
        isinstance(field, ManyToManyField)
    )


def get_out_fields(Model, parent_field, model_stack, excludes, fields):
    out_fields = []
    for field in fields:

        field_name = get_field_name(field, RelatedObject)

        full_field = get_full_field(parent_field, field_name)

        if len([True for exclude in excludes if (exclude in full_field)]):
            continue

        # add to the list
        out_fields.append([full_field, field_name, Model, field.__class__])

        if is_valid_instance(field):

            RelModel = get_rel_model(field, RelatedObject)

            out_fields.extend(
                get_fields(RelModel, full_field, list(model_stack)),
            )

    return out_fields


def get_fields(
    Model,
    parent_field="",
    model_stack=[],
    stack_limit=2,
    excludes=['permissions', 'comment', 'content_type']
):
    """
    Given a Model, return a list of lists of strings with important stuff:
    ...
    ['test_user__user__customuser', 'customuser', 'User', 'RelatedObject']
    ['test_user__unique_id', 'unique_id', 'TestUser', 'CharField']
    ['test_user__confirmed', 'confirmed', 'TestUser', 'BooleanField']
    ...

     """

    # github.com/omab/python-social-auth/commit/d8637cec02422374e4102231488481170dc51057
    if isinstance(Model, basestring):
        app_label, model_name = Model.split('.')
        Model = models.get_model(app_label, model_name)

    fields = Model._meta.fields + \
        Model._meta.many_to_many + \
        Model._meta.get_fields()
    model_stack.append(Model)

    # do a variety of checks to ensure recursion isnt being redundant

    stop_recursion = check_redundant(model_stack, stack_limit)

    if stop_recursion:
        return []  # give empty list for "extend"

    return get_out_fields(Model, parent_field, model_stack, excludes, fields)


def give_model_field(full_field, Model):
    """
    Given a field_name and Model:

    "test_user__unique_id", <AchievedGoal>

    Returns "test_user__unique_id", "id", <Model>, <ModelField>
    """
    field_data = get_fields(Model, '', [])

    for full_key, name, _Model, _ModelField in field_data:
        if full_key == full_field:
            return full_key, name, _Model, _ModelField

    raise Exception('Field key `{0}` not found on `{1}`.'.format(
        full_field, Model.__name__),
    )


def get_simple_fields(Model, **kwargs):
    return [[f[0], f[3].__name__] for f in get_fields(Model, **kwargs)]


def get_user_model():
    # handle 1.7 and back
    try:
        from django.contrib.auth import get_user_model as django_get_user_model
        User = django_get_user_model()
    except ImportError:
        from django.contrib.auth.models import User
    return User
