"""Data access: readers + schema validation.

- Load «DATA_FORMAT» files into a small immutable container (array + metadata).
- Validate fields/dtypes/shapes at the trust boundary; raise with a clear
  message on mismatch.
- No Dash imports here.
