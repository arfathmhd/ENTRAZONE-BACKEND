#!/bin/bash

######################################
# CONFIGURATION - EDIT THESE VALUES
######################################
PROJECT_NAME="ENTRAZONE"       # Django project folder name containing settings.py
PROJECT_DIR="/var/www/ENTRAZONE" # Full path where project will be stored
GIT_REPO="https://github.com/arfathmhd/ENTRAZONE-BACKEND.git" # Your GitHub repo URL
DOMAIN_NAME="entrazone.ibnsu.com"   # Your domain name (without www)
PYTHON_VERSION="python3"
DB_NAME="entrazone"
DB_USER="entrazone_user"
DB_PASSWORD="Entrazone@123"  # Change this to a secure password
DB_HOST="localhost"
######################################

echo "🚀 Starting Django deployment on Ubuntu + Nginx..."

# 1️⃣ Update server and install dependencies
apt update && apt upgrade -y
apt install $PYTHON_VERSION-pip $PYTHON_VERSION-venv $PYTHON_VERSION-dev build-essential libpq-dev postgresql postgresql-contrib nginx git ufw -y

# 2️⃣ Setup PostgreSQL
echo "🗄️ Setting up PostgreSQL..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASSWORD';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET client_encoding TO 'utf8';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET default_transaction_isolation TO 'read committed';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER SET timezone TO 'UTC';"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# 3️⃣ Clone project
mkdir -p $(dirname $PROJECT_DIR)
cd $(dirname $PROJECT_DIR)
if [ ! -d "$PROJECT_DIR" ]; then
    git clone $GIT_REPO $(basename $PROJECT_DIR)
else
    echo "📂 Project already exists, skipping clone."
    cd $PROJECT_DIR
    git pull
fi

# 4️⃣ Setup virtual environment
cd $PROJECT_DIR
$PYTHON_VERSION -m venv venv
source venv/bin/activate

# 5️⃣ Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary

# 6️⃣ Create .env file
echo "⚙️ Creating .env file..."
cat > $PROJECT_DIR/ENTRAZONE/.env <<EOL
DEBUG=False
SECRET_KEY=$(openssl rand -base64 32)
ALLOWED_HOSTS=$DOMAIN_NAME www.$DOMAIN_NAME localhost 127.0.0.1

# Database configuration
DB_NAME=$DB_NAME
DB_USER=$DB_USER
DB_PASSWORD=$DB_PASSWORD
DB_HOST=$DB_HOST
DB_PORT=5432

# Add your API keys and other environment variables here
API_KEY=your_api_key_here
ORG_ID=your_org_id_here
TP_STREAM_URL=your_stream_url_here
EOL

echo "⚠️ IMPORTANT: Update the .env file with your actual API keys and credentials"

# 7️⃣ Django settings
echo "⚙️ Updating Django settings..."
SETTINGS_FILE="$PROJECT_DIR/ENTRAZONE/settings.py"

# Update database settings in settings.py if needed
if grep -q "DATABASES = {" "$SETTINGS_FILE"; then
    echo "Updating database configuration in settings.py..."
    # Create a backup of the settings file
    cp "$SETTINGS_FILE" "${SETTINGS_FILE}.bak"
    
    # This is a simplified approach - for complex settings files, consider using a more robust method
    sed -i '/DATABASES = {/,/}/c\
DATABASES = {\n    "default": {\n        "ENGINE": "django.db.backends.postgresql",\n        "NAME": env("DB_NAME"),\n        "USER": env("DB_USER"),\n        "PASSWORD": env("DB_PASSWORD"),\n        "HOST": env("DB_HOST"),\n        "PORT": env("DB_PORT"),\n    }\n}' "$SETTINGS_FILE"
fi

# 8️⃣ Collect static files and migrate DB
python manage.py collectstatic --noinput
python manage.py migrate

# 9️⃣ Create Gunicorn service
echo "🛠️ Creating Gunicorn service..."
cat > /etc/systemd/system/gunicorn.service <<EOL
[Unit]
Description=gunicorn daemon for $PROJECT_NAME
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind unix:$PROJECT_DIR/gunicorn.sock $PROJECT_NAME.wsgi:application
Environment="DJANGO_SETTINGS_MODULE=$PROJECT_NAME.settings"

[Install]
WantedBy=multi-user.target
EOL

systemctl start gunicorn
systemctl enable gunicorn

# 🔟 Configure Nginx
echo "🌐 Setting up Nginx..."
cat > /etc/nginx/sites-available/$PROJECT_NAME <<EOL
server {
    listen 80;
    server_name $DOMAIN_NAME www.$DOMAIN_NAME;

    location = /favicon.ico { access_log off; log_not_found off; }
    
    location /static/ {
        alias $PROJECT_DIR/static/;
    }
    
    location /media/ {
        alias $PROJECT_DIR/media/;
    }

    location / {
        include proxy_params;
        proxy_pass http://unix:$PROJECT_DIR/gunicorn.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
EOL

ln -sf /etc/nginx/sites-available/$PROJECT_NAME /etc/nginx/sites-enabled
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl restart nginx

# 1️⃣1️⃣ Firewall rules
ufw allow 'Nginx Full'
ufw allow ssh
ufw --force enable

# 1️⃣2️⃣ SSL setup with Certbot
apt install certbot python3-certbot-nginx -y
certbot --nginx -d $DOMAIN_NAME -d www.$DOMAIN_NAME --non-interactive --agree-tos -m admin@$DOMAIN_NAME || echo "⚠️ SSL setup failed. You may need to run this manually once DNS is properly configured."

# 1️⃣3️⃣ Create a script to update the application
cat > $PROJECT_DIR/update.sh <<EOL
#!/bin/bash
cd $PROJECT_DIR
git pull
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart gunicorn
nginx -t && systemctl reload nginx
EOL

chmod +x $PROJECT_DIR/update.sh

echo "✅ Deployment complete! Visit https://$DOMAIN_NAME"
echo ""
echo "To update your application in the future, run: $PROJECT_DIR/update.sh"
echo ""
echo "⚠️ IMPORTANT: Don't forget to update your .env file with proper credentials at:"
echo "$PROJECT_DIR/ENTRAZONE/.env"
