# External CLIs and APIs used

The agent shells out to two Microsoft CLIs and, for a couple of operations, the Power BI
REST API through the Fabric CLI's authenticated proxy.

## powerbi-report-author (Node)

From `@microsoft/powerbi-report-authoring-cli`. Runs anywhere with Node 20+, no Desktop.

- `powerbi-report-author validate <path.pbip>`: schema-validate a project, structured JSON out.
- `powerbi-report-author catalog list`: list visual types.
- `powerbi-report-author catalog describe <visualType>`: roles and formatting objects.
- `powerbi-report-author formatting describe-object <type> <object>`: property names, enums.
- `powerbi-report-author preview-pages | preview-visuals <path>`: read back a project.

## fab (Fabric CLI)

From `ms-fabric-cli`. Authenticates interactively (`fab auth login`).

- `fab ls "/<workspace>"` and `fab get "/<ws>/<item>" -q id`: discover workspaces and item ids.
- `fab import "/<ws>/<Name>.SemanticModel" -i <dir> -f`: deploy the model.
- `fab import "/<ws>/<Name>.Report" -i <dir> -f`: deploy the report.
- `fab api -A powerbi -X post datasets/<id>/refreshes -i '{"notifyOption":"NoNotification"}'`:
  refresh a dataset so inline data loads. Use the non-group `datasets/...` path for a
  personal workspace (the `groups/<id>/...` form returns GroupNotAccessible there).
- `fab api -A powerbi -X post datasets/<id>/executeQueries -i '{"queries":[{"query":"EVALUATE ..."}]}'`:
  run DAX to verify the model actually has data.

## Power BI / Fabric REST endpoints of note

- Dataset refresh: `POST /v1.0/myorg/datasets/{id}/refreshes`
- Execute DAX: `POST /v1.0/myorg/datasets/{id}/executeQueries`
- Report binding rebind uses the report's `definition.pbir` `datasetReference.byConnection`
  with `connectionString: "semanticmodelid=<id>"`.
