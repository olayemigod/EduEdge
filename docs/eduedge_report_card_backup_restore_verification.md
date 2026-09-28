# EduEdge Issued Report Card Backup and Restore Verification

EduEdge official Report Card Issues contain two immutable layers:

1. the frozen report payload stored in the database; and
2. the official PDF stored as a private Frappe File.

A database-only restore is therefore not sufficient for post-#173 issued Report Cards.

## Backup

Create a Frappe backup that includes files:

```bash
bench --site <site> backup --with-files
```

Keep the following outputs from the **same backup run** together:

- database backup;
- public-files backup;
- private-files backup;
- site-config backup;
- backup encryption key where encryption is enabled.

The private-files archive is mandatory for post-#173 official Report Card PDFs.

## Restore

Restore the database and both file archives from the matching backup set:

```bash
bench --site <site> restore <database.sql.gz> \
  --with-public-files <files.tar> \
  --with-private-files <private-files.tar>
```

For encrypted backups, provide the correct Frappe backup encryption key as required by the restore command.

Do not mix the database backup from one timestamp with private files from another timestamp.

After restore:

```bash
bench --site <site> migrate
```

Run normal asset build/cache/restart steps required by the deployment environment.

## Verify issued Report Cards

Read-only summary:

```bash
bench --site <site> execute \
  eduedge.maintenance.report_card_restore.verify_report_card_restore_integrity
```

Optional bounded settings:

```bash
bench --site <site> execute \
  eduedge.maintenance.report_card_restore.verify_report_card_restore_integrity \
  --kwargs '{"batch_size":25,"max_problem_rows":100}'
```

Deployment/restore gate that fails when any non-legacy Issue has an integrity problem:

```bash
bench --site <site> execute \
  eduedge.maintenance.report_card_restore.assert_report_card_restore_integrity
```

## Interpretation

- **Healthy**: immutable payload and official private PDF both verify.
- **Legacy**: payload verifies, but the Issue predates immutable PDF archival. This is a warning, not corruption.
- **Problem**: payload or PDF integrity failed. The gate must fail.

The verifier checks the full site in bounded batches and reports only a bounded number of problem rows. It does not mutate Issues, Files, results, publications, or reviews.

## If verification fails

Do not regenerate, overwrite, delete, or patch an issued Report Card to make the check pass.

1. Identify the failed Issue and failure class.
2. Confirm the database and private-files archives came from the same backup set.
3. Restore the correct private-files archive when the File is missing or mismatched.
4. If the immutable database payload itself is corrupt, restore the correct database backup rather than editing the Issue.
5. Run migration if required.
6. Re-run the fail-closed integrity gate.
7. Use **Results Audit → Issued Report Integrity** for permission-aware investigation and bounded CSV evidence.

A genuine academic correction must use the normal Result Publication / Report Card Review / new Issue workflow. It must not mutate historical issued evidence.
