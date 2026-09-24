"""File upload validation for DAS Document models.

Enforces an extension whitelist, a size ceiling, and a compression/archive
policy on user-uploaded files, so a save() can never persist an unexpected
file type (executables, scripts, disguised binaries) or an unsafe/nested
archive.
"""
import logging
import os
import zipfile

from django.conf import settings
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)

STANDARD_ALLOWED_EXTENSIONS = frozenset({
    ".pdf", ".png", ".jpg", ".jpeg", ".doc", ".docx",
    ".xls", ".xlsx", ".csv", ".txt", ".msg", ".eml",
})

GIS_ARCHIVE_ALLOWED_EXTENSIONS = frozenset({
    ".shp", ".shx", ".dbf", ".prj", ".sbn", ".sbx", ".cpg", ".qix", ".xml",
})

COMPRESSED_EXTENSIONS = frozenset({".zip"})

DEFAULT_MAX_UPLOAD_SIZE = getattr(settings, "FILE_UPLOAD_MAX_MEMORY_SIZE", 15 * 1024 * 1024)

# Defence in depth against zip/decompression bombs; not part of the literal
# whitelist spec but a direct consequence of parsing attacker-controlled zips.
MAX_ARCHIVE_UNCOMPRESSED_SIZE = 100 * 1024 * 1024  # 100 MB


def validate_uploaded_file(
    file_obj,
    allowed_extensions=STANDARD_ALLOWED_EXTENSIONS,
    allow_compressed=False,
    max_upload_size=DEFAULT_MAX_UPLOAD_SIZE,
):
    """Validate a single uploaded file object against the DAS whitelist policy.

    `file_obj` is anything exposing `.name` and `.size`/file-like read/seek
    (a Django `UploadedFile`, `FieldFile`, or `ContentFile`). Raises
    `django.core.exceptions.ValidationError` on any violation; returns None
    (no value) when the file is acceptable.
    """
    name = getattr(file_obj, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()

    size = getattr(file_obj, "size", None)
    if size is not None and size > max_upload_size:
        raise ValidationError(
            f"File '{name}' ({size} bytes) exceeds the maximum allowed size "
            f"of {max_upload_size} bytes."
        )

    if ext in COMPRESSED_EXTENSIONS:
        if not allow_compressed:
            raise ValidationError(
                f"Compressed/archive files ('{ext}') are not permitted for this document type."
            )
        _validate_archive(file_obj, name)
        return

    if ext not in allowed_extensions:
        raise ValidationError(
            f"File extension '{ext}' is not permitted. "
            f"Allowed extensions: {', '.join(sorted(allowed_extensions))}."
        )


def _validate_archive(file_obj, name):
    try:
        file_obj.seek(0)
    except (AttributeError, ValueError):
        pass

    try:
        with zipfile.ZipFile(file_obj) as archive:
            total_uncompressed = 0
            for info in archive.infolist():
                if info.is_dir():
                    continue
                member_path = info.filename.strip("/")
                member_ext = os.path.splitext(member_path)[1].lower()

                if member_ext in COMPRESSED_EXTENSIONS:
                    raise ValidationError(
                        f"Nested archive '{member_path}' inside '{name}' is not allowed "
                        f"(recursive/nested archives are forbidden)."
                    )
                if "/" in member_path:
                    raise ValidationError(
                        f"Archive '{name}' contains a nested folder ('{member_path}'); "
                        f"only a flat (depth 1) file listing is allowed."
                    )
                if member_ext not in GIS_ARCHIVE_ALLOWED_EXTENSIONS:
                    raise ValidationError(
                        f"Archive '{name}' contains a disallowed file '{member_path}' "
                        f"(extension '{member_ext}')."
                    )

                total_uncompressed += info.file_size
                if total_uncompressed > MAX_ARCHIVE_UNCOMPRESSED_SIZE:
                    raise ValidationError(
                        f"Archive '{name}' exceeds the maximum allowed uncompressed size "
                        f"of {MAX_ARCHIVE_UNCOMPRESSED_SIZE} bytes."
                    )
    except zipfile.BadZipFile:
        raise ValidationError(f"'{name}' is not a valid zip archive.")
    finally:
        try:
            file_obj.seek(0)
        except (AttributeError, ValueError):
            pass


class SanitiseFileMixin:
    """Model mixin enforcing the DAS file whitelist/compression policy on save()/clean().

    Must be a leftmost base class ahead of models.Model, e.g.:
        class ApprovalDocument(SanitiseFileMixin, Document):
            ...

    Class-level configuration (declared on the concrete model):
        sanitise_file_field: name of the FileField attribute to validate
            (default "_file", matching the DAS Document convention).
        allowed_extensions: whitelist of standard extensions
            (default STANDARD_ALLOWED_EXTENSIONS).
        allow_compressed: whether a .zip archive is accepted at all
            (default False).
        max_upload_size: max bytes accepted (default DEFAULT_MAX_UPLOAD_SIZE).
    """

    sanitise_file_field = "_file"
    allowed_extensions = STANDARD_ALLOWED_EXTENSIONS
    allow_compressed = False
    max_upload_size = DEFAULT_MAX_UPLOAD_SIZE

    def _validate_sanitised_file(self):
        file_obj = getattr(self, self.sanitise_file_field, None)
        if not file_obj:
            return
        validate_uploaded_file(
            file_obj,
            allowed_extensions=self.allowed_extensions,
            allow_compressed=self.allow_compressed,
            max_upload_size=self.max_upload_size,
        )

    def clean(self):
        super_clean = getattr(super(), "clean", None)
        if callable(super_clean):
            super_clean()
        self._validate_sanitised_file()

    def save(self, *args, **kwargs):
        self._validate_sanitised_file()
        super().save(*args, **kwargs)
