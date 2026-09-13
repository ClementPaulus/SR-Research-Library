## Research Library change

- Object(s) affected:
- AuthorID(s):
- SourceID(s):
- RelationID(s):
- Schema version:
- Taxonomy version:
- Admission outcome(s) and receipt ID(s):
- Open seams touched (`releases/open-seams.yaml`):

### Checks

- [ ] `python -m validators.validate`
- [ ] `python -m pytest`
- [ ] `python -m validators.build_site` (site regenerated from the registry)
- [ ] No frozen GCD object was modified.
- [ ] No unsupported metadata was invented; gaps are declared in `missingness`.
- [ ] Any new controlled term is recorded in `taxonomy/extensions.yaml`.
