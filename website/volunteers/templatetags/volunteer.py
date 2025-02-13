from django import template

register = template.Library()


@register.filter
def for_event(volunteer, event):
    va = volunteer.volunteeravailability_set.filter(event=event)
    if len(va) != 1:
        return None
    return va[0]


@register.filter
def available_from(va, from_):
    return va, from_


@register.filter
def available_for(va_from_, for_):
    availabilities, from_ = va_from_
    if availabilities is None:
        return False
    return availabilities.is_available_at(from_, for_)


@register.filter
def id(o):
    if o is None:
        return ""
    return o.id


@register.filter
def slug(o):
    if o is None:
        return ""
    return o.slug


# TODO use Internationalization
@register.filter
def schedule_type_name(o):
    if o == "G":
        return "Généré"
    elif o == "B":
        return "Base"
    elif o == "E":
        return "Vide"
    return ""
