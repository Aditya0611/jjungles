# Docker Setup Guide for JJ Trend Widget

This guide explains how to run the JJ Trend Widget Odoo module using Docker.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+
- At least 2GB of free disk space

## Quick Start

### 1. Start the Services

```bash
# From the project root directory
docker-compose up -d
```

This will:
- Start a PostgreSQL 15 database container
- Start an Odoo 16 container with your module mounted
- Expose Odoo on `http://localhost:8069`

### 2. Access Odoo

1. Open your browser and go to: `http://localhost:8069`
2. You'll see the Odoo database creation screen
3. Create a new database:
   - **Database Name**: `jj_trend_db` (or any name you prefer)
   - **Email**: Your admin email
   - **Password**: Your admin password
   - **Language**: Your preferred language
   - **Country**: Your country
   - **Demo data**: Check if you want sample data

### 3. Install the Module

1. After database creation, go to **Apps** menu
2. Remove the "Apps" filter (click the X)
3. Click **Update Apps List** (⟳ icon)
4. Search for "JJ Trend Engine"
5. Click **Install**

### 4. Configure Supabase

1. Go to **Settings** → **Technical** → **Parameters** → **System Parameters**
2. Create two parameters:

   **Parameter 1:**
   - Key: `jj_trend.supabase_url`
   - Value: `https://your-project.supabase.co`

   **Parameter 2:**
   - Key: `jj_trend.supabase_key`
   - Value: `your-supabase-anon-key`

3. Save both parameters

### 5. Verify Installation

Navigate to: **Trend Engine** → **Raw Trend Data**

You should see the admin view. If no data appears, verify your Supabase credentials and ensure your Supabase table has data.

## Docker Commands

### View Logs

```bash
# All services
docker-compose logs -f

# Just Odoo
docker-compose logs -f odoo

# Just database
docker-compose logs -f db
```

### Stop Services

```bash
docker-compose stop
```

### Start Services

```bash
docker-compose start
```

### Stop and Remove Containers (keeps data)

```bash
docker-compose down
```

### Stop and Remove Everything (including volumes - **WARNING: deletes data**)

```bash
docker-compose down -v
```

### Restart Odoo (useful after code changes)

```bash
docker-compose restart odoo
```

### Access Odoo Shell

```bash
docker-compose exec odoo odoo shell -d your_database_name
```

### Access Database

```bash
docker-compose exec db psql -U odoo -d postgres
```

## Development Workflow

### Making Code Changes

1. Edit your code in `jj_trend_widget2/`
2. Restart Odoo container:
   ```bash
   docker-compose restart odoo
   ```
3. In Odoo, upgrade the module:
   - Go to **Apps** → Find "JJ Trend Engine" → Click **Upgrade**

### Hot Reload (Development Mode)

The `docker-compose.yml` includes development mode flags:
- `--dev=reload,qweb,werkzeug,xml`

This enables:
- **reload**: Auto-reload Python code changes (restart still recommended)
- **qweb**: Reload QWeb templates
- **werkzeug**: Enable Werkzeug debugger
- **xml**: Reload XML views

After code changes:
1. Restart Odoo: `docker-compose restart odoo`
2. Clear browser cache (Ctrl+Shift+R)

## Configuration

### Custom Odoo Configuration

Edit `odoo.conf` to customize:
- Log levels
- Database settings
- Addon paths
- Other Odoo options

### Environment Variables

You can override environment variables in `docker-compose.yml`:

```yaml
environment:
  - HOST=db
  - USER=odoo
  - PASSWORD=odoo
  - PGDATABASE=postgres
```

### Port Configuration

To change the Odoo port, modify `docker-compose.yml`:

```yaml
ports:
  - "8080:8069"  # Change 8080 to your preferred port
```

## Troubleshooting

### Module Not Appearing in Apps

1. Check logs: `docker-compose logs odoo`
2. Verify module path: Ensure `jj_trend_widget2` is in `/mnt/extra-addons/`
3. Restart Odoo: `docker-compose restart odoo`
4. Update Apps List in Odoo UI

### Database Connection Errors

1. Check if database container is running: `docker-compose ps`
2. Check database logs: `docker-compose logs db`
3. Verify database is healthy: `docker-compose exec db pg_isready -U odoo`

### Permission Errors

If you encounter permission errors:

```bash
# Fix ownership (Linux/Mac)
sudo chown -R 101:101 ./jj_trend_widget2

# Or run with user mapping
# Add to docker-compose.yml under odoo service:
user: "${UID}:${GID}"
```

### Out of Memory

If Odoo crashes due to memory:

1. Increase Docker memory limit in Docker Desktop settings
2. Or add memory limit to docker-compose.yml:
   ```yaml
   odoo:
     deploy:
       resources:
         limits:
           memory: 2G
   ```

### Clear Everything and Start Fresh

```bash
# Stop and remove everything
docker-compose down -v

# Remove images (optional)
docker rmi odoo:16 postgres:15

# Start fresh
docker-compose up -d
```

## Production Considerations

⚠️ **This setup is for development only!**

For production:

1. **Change default passwords** in `docker-compose.yml` and `odoo.conf`
2. **Use environment variables** for sensitive data (don't commit passwords)
3. **Set up proper backups** for the database volume
4. **Use reverse proxy** (nginx/traefik) with SSL
5. **Remove development mode** flags
6. **Set appropriate log levels**
7. **Configure resource limits**
8. **Use secrets management** for API keys

Example production `docker-compose.yml` snippet:

```yaml
services:
  odoo:
    environment:
      - HOST=${DB_HOST}
      - USER=${DB_USER}
      - PASSWORD=${DB_PASSWORD}
    command: >
      -- --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons
      -- --without-demo=all
      -- --log-level=warn
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

## Data Persistence

Data is stored in Docker volumes:
- `odoo-db-data`: PostgreSQL data
- `odoo-web-data`: Odoo filestore and sessions

To backup:

```bash
# Backup database
docker-compose exec db pg_dump -U odoo postgres > backup.sql

# Backup volumes
docker run --rm -v jjungles_odoo-db-data:/data -v $(pwd):/backup alpine tar czf /backup/db-backup.tar.gz /data
```

## Support

For issues:
1. Check Docker logs: `docker-compose logs`
2. Check Odoo logs inside container: `docker-compose exec odoo cat /var/log/odoo/odoo.log`
3. Verify Supabase configuration
4. Ensure module is properly installed

