# rpc-7004 DocOps Logic example

```bash
python3 ../../scripts/dol.py init rpc-7004
python3 ../../scripts/dol.py ch add --stage s03 --pr 128 --slug simd-intrin-rewrite
python3 ../../scripts/dol.py va add --stage s03 --pr 128 --result pass
python3 ../../scripts/dol.py lint --soft
python3 ../../scripts/dol.py solve --stub --mode repair
```

Expected shape:

```json
{"solver":"stub","mode":"repair","status":"feasible","fix":[],"cost":0,"rules":[]}
```
