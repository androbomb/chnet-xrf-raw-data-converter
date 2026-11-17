"""xrfraw error types."""


class XRFReadError(Exception):
    """Malformed raw content or out-of-range data (line number when known)."""

    def __init__(self, line_no, msg):
        self.line_no = line_no
        super().__init__(f"line {line_no}: {msg}" if line_no is not None else msg)


class MetadataConflictError(Exception):
    """External metadata contradicts the file's XML metadata (no silent overwrite)."""

    def __init__(self, field, base_value, ext_value):
        self.field = field
        self.base_value = base_value
        self.ext_value = ext_value
        super().__init__(
            f"metadata conflict on '{field}': file={base_value} vs external={ext_value}"
        )
