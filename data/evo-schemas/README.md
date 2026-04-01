# Local Evo Schemas Backup

This directory is reserved for a repository-managed backup of the `schema/objects`
tree from `SeequentEvo/evo-schemas`.

The integration planning tool prefers this backup to avoid GitHub API rate limits.

Expected layout:

```text
data/evo-schemas/schema/objects/
  downhole-collection/
    1.0.1/
    1.1.0/
  geological-model-meshes/
    2.2.0/
  ...
```

If you want to refresh the backup manually, copy the upstream `schema/objects`
directory from `SeequentEvo/evo-schemas` into `data/evo-schemas/schema/objects`.