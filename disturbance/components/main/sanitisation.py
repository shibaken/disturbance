"""Input sanitisation utilities for DAS user-supplied text and JSON data.

Uses nh3 (Ammonia-based HTML sanitiser) to strip HTML/script content from
free-text CharField/TextField values and from string leaves inside JSONField
payloads, so that stored data cannot be used for stored XSS when later
rendered by the frontend or any HTML-emitting view/report.
"""
import logging

import nh3
from django.core.exceptions import ValidationError
from django.db import models

logger = logging.getLogger(__name__)

# HTML entities nh3 leaves behind after stripping tags; un-escaped so plain
# text is stored naturally instead of double-escaped (e.g. "Tom & Jerry"
# should be stored as "Tom & Jerry", not "Tom &amp; Jerry").
_ENTITY_UNESCAPES = (
    ("&amp;", "&"),
    ("&quot;", '"'),
    ("&#39;", "'"),
)


def neutralise_html(value: str) -> str:
    """Strip HTML/script markup from a plain-text string using nh3.

    Falls back to returning the original value unchanged if nh3 raises an
    unexpected error, so a sanitiser bug can never surface as a 500 error to
    the end user.
    """
    if not isinstance(value, str) or not value:
        return value
    try:
        cleaned = nh3.clean(value, tags=set(), attributes={})
        for escaped, plain in _ENTITY_UNESCAPES:
            cleaned = cleaned.replace(escaped, plain)
        return cleaned
    except Exception:
        logger.exception("nh3 sanitisation failed for value; returning original")
        return value


def _sanitise_json_value(value):
    """Recursively sanitise a JSON-compatible Python value (dict/list/str/etc).

    - String leaves are passed through neutralise_html().
    - Dict keys that themselves contain HTML/tag markup are dropped, since a
      key is never expected to legitimately carry markup and this closes off
      a JSON-key-based injection vector.
    - Non-string primitives (int, float, bool, None) are returned unchanged.
    """
    if isinstance(value, dict):
        sanitised = {}
        for key, val in value.items():
            if isinstance(key, str) and neutralise_html(key) != key:
                # Key contains HTML/tag markup - drop the entry rather than
                # silently rewrite the key under it.
                logger.warning("Dropping JSON key containing HTML markup: %r", key)
                continue
            sanitised[key] = _sanitise_json_value(val)
        return sanitised
    if isinstance(value, list):
        return [_sanitise_json_value(item) for item in value]
    if isinstance(value, str):
        return neutralise_html(value)
    return value


class SanitisationModelMixin:
    """Model mixin that sanitises CharField/TextField/JSONField values on save().

    Must be the leftmost base class, e.g.:
        class MyModel(SanitisationModelMixin, models.Model):
            ...

    Class-level configuration (declared on the concrete model):
        sanitise_exclude_fields: set[str] of field names to skip entirely
            (e.g. rich-text/TinyMCE HTMLField columns).
        sanitise_reject_fields: set[str] of field names that must raise a
            ValidationError if sanitisation would change the incoming value,
            instead of silently rewriting it.
    """

    sanitise_exclude_fields: set = set()
    sanitise_reject_fields: set = set()

    def _sanitisable_fields(self):
        for field in self._meta.get_fields():
            if field.name in self.sanitise_exclude_fields:
                continue
            if isinstance(field, models.JSONField):
                yield field.name, "json"
            elif isinstance(field, (models.CharField, models.TextField)):
                yield field.name, "text"

    def _sanitise_fields(self):
        for field_name, kind in self._sanitisable_fields():
            original = getattr(self, field_name, None)
            if original is None:
                continue
            if kind == "json":
                cleaned = _sanitise_json_value(original)
            else:
                if not isinstance(original, str):
                    continue
                cleaned = neutralise_html(original)
            if cleaned != original:
                if field_name in self.sanitise_reject_fields:
                    raise ValidationError(
                        f"Field '{field_name}' contains disallowed HTML/script content."
                    )
                setattr(self, field_name, cleaned)

    def save(self, *args, **kwargs):
        self._sanitise_fields()
        super().save(*args, **kwargs)


class NH3SanitizeSerializerMixin:
    """DRF serializer mixin that sanitises string/JSON input during validate().

    Applies to the resolved `attrs` dict for every CharField/JSONField backed
    attribute, honouring an optional `sanitise_exclude_fields` set declared on
    the serializer class (mirrors SanitisationModelMixin's naming).
    """

    sanitise_exclude_fields: set = set()

    def validate(self, attrs):
        attrs = super().validate(attrs)
        for field_name, value in list(attrs.items()):
            if field_name in self.sanitise_exclude_fields:
                continue
            if isinstance(value, str):
                attrs[field_name] = neutralise_html(value)
            elif isinstance(value, (dict, list)):
                attrs[field_name] = _sanitise_json_value(value)
        return attrs
