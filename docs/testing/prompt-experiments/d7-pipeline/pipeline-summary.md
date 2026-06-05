# D7 Pipeline Dry-run Summary

- **Phase**: T3-D7.8
- **Pipeline**: d7_quality_engine_dryrun
- **LLM Called**: False
- **Used Existing Review Output**: True
- **Auto Write Scene**: False
- **Auto Write Settings**: False

## Steps

| Step | Status |
|------|--------|
| diff_engine | ✅ passed |
| review_engine | ✅ passed |
| review_validator | ✅ passed |
| state_snapshot | ✅ passed |
| plot_debt | ✅ passed |
| rewrite_engine | ✅ passed |

## Summary

- **Candidates**: 14
- **Reviews**: 14
- **Snapshot Updates**: 0
- **Plot Debts**: 25
- **Rewrite Suggestions**: 5

## Known Diff Noise

> **Note**: These are candidate noise, NOT confirmed settings. They will be reviewed/ignored downstream.

| Entity | Reason |
|--------|--------|
| 着昏黄的灯 | Diff Engine candidate noise; should be reviewed/ignored downstream |
| 李玄推阁 | Diff Engine candidate noise; should be reviewed/ignored downstream |

**Timestamp**: 2026-06-05T18:43:10.154253