# Skills

This agent's report authoring builds on Microsoft's official agent skills and CLIs:

- **microsoft/skills-for-fabric**: https://github.com/microsoft/skills-for-fabric
  - `powerbi-report-authoring`: create and modify PBIR report files (pages, visuals, filters,
    slicers, themes) and validate them.
  - `semantic-model-authoring`: author TMDL semantic models (tables, measures, partitions).

Rather than vendor Microsoft's skill content here, install their CLIs (see the root README)
and, if you drive this repo with an agent framework that supports skills, point it at the
`skills-for-fabric` plugin directories.

## Using this repo as a skill

The three tools in `src/pbi_report_agent/` (generate, validate, publish) are the primitives
an agent needs. `agent.py` already wraps them as a Deep Agent. To expose them to a different
harness, register the same three functions as tools and reuse the system prompt in `agent.py`.
