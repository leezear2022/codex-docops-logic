# rpc-7004 DocOps Logic example

```powershell
& ..\..\scripts\dol.ps1 init rpc-7004
& ..\..\scripts\dol.ps1 ch add --stage s03 --pr 128 --slug simd-intrin-rewrite
& ..\..\scripts\dol.ps1 va add --stage s03 --pr 128 --result pass
& ..\..\scripts\dol.ps1 lint --soft
& ..\..\scripts\dol.ps1 solve --stub --mode repair
```

Expected shape:

```json
{"solver":"stub","mode":"repair","status":"feasible","fix":[],"cost":0,"rules":[]}
```
