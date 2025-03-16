# Database Migration Guide

## Basic Operations

### Creating a New Migration
```bash
flask db migrate -m "description of your changes"
```

## Troubleshooting

### Resolving Multiple Head Revisions Error

If you encounter this error:

```bash
ERROR [flask_migrate] Error: Multiple head revisions are present for given argument 'head'; 
please specify a specific target revision, '<branchname>@head' to narrow to a specific head, 
or 'heads' for all heads
```

Follow these steps to resolve it:

1. **Show current heads**
   ```bash
   flask db heads
   ```

2. **Create a merge migration**
   ```bash
   flask db merge heads
   ```
   This creates a new migration file that merges all divergent heads into a single revision.
   The new migration will have empty `upgrade()` and `downgrade()` functions since it's just connecting branches.

3. **Apply the merge migration**
   ```bash
   flask db upgrade
   ```
   This migrates the database to the newest version.

