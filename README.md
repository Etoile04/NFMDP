# NFM — Nuclear Fuel Material Unified Platform

Unified integration platform merging NFMD, NucPot, OntoFuel, and NucPot-AutoVC data into a single schema.

## Project Structure

```
nfm/
├── supabase/
│   └── migrations/     # Schema DDL + data migration scripts
├── docs/               # Architecture docs and design decisions
└── scripts/            # Utility and migration helper scripts
```

## Migration Files

| File | Purpose |
|------|---------|
| 001–008 | Unified schema DDL (from NFM-6) |
| 009 | NFMD v2 → Unified schema data migration |
| 010 | Migration validation checks |

## Source Projects

- **NFMD** — Nuclear Fuel Material Database (16,379 parameters)
- **NucPot** — Interatomic Potential Library
- **OntoFuel** — Ontology-driven knowledge management
- **NucPot-AutoVC** — Automated verification system

## Development

Dual-track development: this repo is separate from individual source projects to avoid schema confusion during migration.
