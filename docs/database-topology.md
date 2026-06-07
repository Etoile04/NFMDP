# NFM Database Topology

## Local Development Databases

| Instance | Container | Port | Contents |
|----------|-----------|------|----------|
| nucpot | supabase_db_nucpot | 54428 | NucPot potentials, reference_values, verifications |
| workspace | supabase_db_workspace | 54322 | NFMD v2 source data (16,379 params, 163 lit, 89 materials) |
| **nfm** | Use workspace | 54322 | NFM unified schema + migrated data |

## Migration Strategy

1. Apply unified schema DDL (001-008) to workspace database
2. Run migration 009 against workspace DB — reads from NFMD v2 tables (renamed to `_src_*`), writes to unified tables
3. Run validation 010 against workspace DB

## Backup Location

All pre-migration backups stored in `/Users/lwj04/Projects/nfm-backups/`

## Dual-Track Development

- **Track 1 (nucpot)**: `supabase_db_nucpot:54428` — existing NucPot platform, unchanged
- **Track 2 (nfm)**: `supabase_db_workspace:54322` — new unified NFM platform
- Code: `github.com/Etoile04/nfm` — separate repo for NFM migration work
