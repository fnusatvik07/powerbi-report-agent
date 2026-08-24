# Architecture

The agent turns a natural-language request into a published Power BI report through a
deterministic author -> validate -> fix -> publish loop. See `architecture.png` for the
diagram (source: `architecture.drawio`, exported with the draw.io CLI).

## The PBIP project format

A Power BI project on disk is two items:

```
<Name>.SemanticModel/     the data model, in TMDL
  definition.pbism
  definition/database.tmdl, model.tmdl, tables/<Table>.tmdl
<Name>.Report/            the visuals, in PBIR (JSON)
  definition.pbir         binding to the semantic model
  definition/report.json, pages/pages.json, pages/<id>/page.json + visuals/<id>/visual.json
<Name>.pbip               a shortcut manifest
```

PBIR became the default Power BI report format in 2026, which is what makes code-first
authoring by an agent fully supported rather than a hack.

## Load-bearing details learned against the live service

These are the non-obvious rules the generator and publisher encode:

- `database.tmdl` must begin with a `database <id>` object declaration, not a bare property.
- `model.tmdl` must set `defaultPowerBIDataSourceVersion: powerBI_V3` for an import-mode
  model, or the service rejects it with "Import from JSON supported for V3 models only".
- Inline sample data is a Power Query `#table(...)` expression, so the model refreshes in the
  cloud with no gateway or external source.
- `report.json` must contain a `themeCollection.baseTheme` with `type` (`SharedResources`)
  and a string `reportVersionAtImport`.
- On publish, the report cannot keep its local `byPath` binding. It must be rebound to
  `byConnection`, and that block accepts only a `connectionString` string of the form
  `semanticmodelid=<id>`. Any other field is rejected by the service schema.
- Import the semantic model before the report, then read back the deployed model id.
- Trigger a dataset refresh after import, or the report renders empty (the inline data has
  not loaded yet). This is the single most common "my report is blank" cause.

## The fix loop

`powerbi-report-author validate` returns structured diagnostics (error count plus messages
with file and JSON path). The agent reads these, corrects its spec, and regenerates until
the result is `succeeded`. This is why an agent can author reliably: it is not guessing, it
is reacting to a real validator.
