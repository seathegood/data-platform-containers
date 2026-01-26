# Runbooks

This directory holds operational runbooks for production incidents, migrations, and other non-routine tasks. Add markdown files here as you build out container packages that require special operating procedures.

Suggested initial runbooks:
- Rotate GHCR credentials and validate pushes.
- Refresh base image digests and rerun smokes (Airflow, Spark).
- Hotfix flow for critical CVEs (bump base, rebuild, republish).
- Restore devpi-server data from backups.
