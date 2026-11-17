"""UI: factory + callbacks + figures.

- `build_app(data_or_path=None)` returns the app object; a None/empty start
  means "no data loaded" (upload/link in the UI).
- Keep callbacks directly callable from tests (no browser, no live server).
- Look: dbc DARKLY, navbar accent #4196B4, fluid container, main view left
  (5 cols) / detail view right (7 cols).
