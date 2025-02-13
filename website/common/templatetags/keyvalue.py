from django import template

register = template.Library()


@register.filter
def keyvalue(dict, key):
    if key in dict:
        return dict[key]
    return None


@register.filter
def haskey(dict, key):
    return key in dict


@register.filter
def make_tuple(val1, val2):
    return (val1, val2)
