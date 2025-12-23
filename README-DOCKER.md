# Docker Setup Guide for ENTRAZONE Backend

This guide explains how to run the ENTRAZONE Django backend using Docker and Docker Compose.

## Prerequisites

- Docker (version 20.10 or higher)
- Docker Compose (version 2.0 or higher)

### Installation

**macOS:**
```bash
brew install docker docker-compose
```

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install docker.io docker-compose-plugin
```

**Windows:**
Download and install [Docker Desktop](https://www.docker.com/products/docker-desktop)

## Quick Start

### 1. Environment Setup

Copy the example environment file and configure it:

```bash
cp .env.example ENTRAZONE/.env
```

Edit `ENTRAZONE/.env` and update the following critical values:

```bash
# Generate a secure secret key
SECRET_KEY=$(openssl rand -base64 32)

# Set a secure database password
DB_PASSWORD=your_secure_password_here

# Add your API credentials
API_KEY=your_actual_api_key
ORG_ID=your_actual_org_id
TP_STREAM_URL=your_actual_stream_url
```

> **Important:** For Docker, ensure `DB_HOST=db` (not `localhost`)

### 2. Build and Start Containers

```bash
# Build the Docker images
docker-compose build

# Start all services in detached mode
docker-compose up -d
```

### 3. Run Database Migrations

```bash
docker-compose exec web python manage.py migrate
```

### 4. Create a Superuser

```bash
docker-compose exec web python manage.py createsuperuser
```

### 5. Access the Application

- **Application:** http://localhost:8000
- **Admin Panel:** http://localhost:8000/admin

## Common Commands

### Container Management

```bash
# Start containers
docker-compose up -d

# Stop containers
docker-compose down

# Restart containers
docker-compose restart

# View running containers
docker-compose ps

# Stop and remove all containers, networks, and volumes
docker-compose down -v
```

### Logs and Debugging

```bash
# View logs from all services
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs for specific service
docker-compose logs web
docker-compose logs db

# View last 100 lines
docker-compose logs --tail=100 web
```

### Django Management Commands

```bash
# Run any Django management command
docker-compose exec web python manage.py <command>

# Examples:
docker-compose exec web python manage.py makemigrations
docker-compose exec web python manage.py migrate
docker-compose exec web python manage.py createsuperuser
docker-compose exec web python manage.py collectstatic
docker-compose exec web python manage.py shell
```

### Database Management

```bash
# Access PostgreSQL shell
docker-compose exec db psql -U entrazone_user -d entrazone

# Backup database
docker-compose exec db pg_dump -U entrazone_user entrazone > backup.sql

# Restore database
docker-compose exec -T db psql -U entrazone_user entrazone < backup.sql

# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
docker-compose exec web python manage.py migrate
```

### Rebuilding After Code Changes

```bash
# Rebuild and restart after code changes
docker-compose up -d --build

# Force rebuild without cache
docker-compose build --no-cache
docker-compose up -d
```

## File Structure

```
ENTRAZONE-BACKEND/
├── Dockerfile              # Docker image definition
├── docker-compose.yml      # Multi-container orchestration
├── .dockerignore          # Files excluded from Docker build
├── .env.example           # Environment variables template
├── ENTRAZONE/
│   └── .env              # Actual environment variables (not in git)
├── media/                # User-uploaded files (persisted)
├── static/               # Static files (persisted)
└── requirements.txt      # Python dependencies
```

## Environment Variables

Key environment variables in `ENTRAZONE/.env`:

| Variable | Description | Example |
|----------|-------------|---------|
| `DEBUG` | Enable debug mode | `True` or `False` |
| `SECRET_KEY` | Django secret key | Generate with `openssl rand -base64 32` |
| `ALLOWED_HOSTS` | Allowed hostnames | `localhost 127.0.0.1 yourdomain.com` |
| `DB_HOST` | Database hostname | `db` (for Docker) |
| `DB_NAME` | Database name | `entrazone` |
| `DB_USER` | Database user | `entrazone_user` |
| `DB_PASSWORD` | Database password | Your secure password |
| `DB_PORT` | Database port | `5432` |

## Troubleshooting

### Port Already in Use

If port 8000 or 5432 is already in use:

```bash
# Change ports in docker-compose.yml
# For web service: "8001:8000"
# For db service: "5433:5432"
```

### Database Connection Issues

```bash
# Check if database is healthy
docker-compose ps

# View database logs
docker-compose logs db

# Ensure DB_HOST=db in ENTRAZONE/.env
```

### Permission Denied Errors

```bash
# Fix media/static folder permissions
sudo chown -R $USER:$USER media static assets
```

### Container Won't Start

```bash
# View detailed logs
docker-compose logs web

# Check container status
docker-compose ps

# Remove and recreate containers
docker-compose down
docker-compose up -d
```

### Static Files Not Loading

```bash
# Collect static files
docker-compose exec web python manage.py collectstatic --noinput

# Restart web service
docker-compose restart web
```

## Production Deployment

For production deployment, make these changes:

### 1. Update Environment Variables

```bash
DEBUG=False
SECRET_KEY=<generate-strong-secret-key>
ALLOWED_HOSTS=yourdomain.com www.yourdomain.com
```

### 2. Use External Database

Consider using a managed PostgreSQL service (AWS RDS, DigitalOcean Managed Database, etc.) instead of containerized database.

### 3. Configure Reverse Proxy

Use Nginx or Traefik as a reverse proxy with SSL/TLS:

```yaml
# Example nginx configuration
server {
    listen 80;
    server_name yourdomain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /static/ {
        alias /path/to/static/;
    }
    
    location /media/ {
        alias /path/to/media/;
    }
}
```

### 4. Enable HTTPS

```bash
# Install certbot
sudo apt-get install certbot python3-certbot-nginx

# Get SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com
```

### 5. Set Up Monitoring

- Configure logging to external service
- Set up health checks
- Monitor container resource usage

## Additional Resources

- [Django Documentation](https://docs.djangoproject.com/)
- [Docker Documentation](https://docs.docker.com/)
- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

## Support

For issues specific to this Docker setup, check:
1. Container logs: `docker-compose logs`
2. Django logs: `docker-compose exec web python manage.py check`
3. Database connectivity: `docker-compose exec web python manage.py dbshell`
