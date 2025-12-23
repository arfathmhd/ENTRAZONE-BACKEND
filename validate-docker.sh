#!/bin/bash

# Docker Configuration Validation Script for ENTRAZONE Backend
# This script checks your Docker setup before running containers

echo "🔍 Docker Configuration Validation"
echo "===================================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

ERRORS=0
WARNINGS=0

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        ERRORS=$((ERRORS + 1))
    fi
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
    WARNINGS=$((WARNINGS + 1))
}

# 1. Check if required files exist
echo "📁 Checking Required Files..."
[ -f "Dockerfile" ] && print_status 0 "Dockerfile exists" || print_status 1 "Dockerfile missing"
[ -f "docker-compose.yml" ] && print_status 0 "docker-compose.yml exists" || print_status 1 "docker-compose.yml missing"
[ -f ".dockerignore" ] && print_status 0 ".dockerignore exists" || print_status 1 ".dockerignore missing"
[ -f "requirements.txt" ] && print_status 0 "requirements.txt exists" || print_status 1 "requirements.txt missing"
[ -f "ENTRAZONE/.env" ] && print_status 0 "ENTRAZONE/.env exists" || print_status 1 "ENTRAZONE/.env missing"
[ -f "manage.py" ] && print_status 0 "manage.py exists" || print_status 1 "manage.py missing"
echo ""

# 2. Check Docker installation
echo "🐳 Checking Docker Installation..."
if command -v docker &> /dev/null; then
    DOCKER_VERSION=$(docker --version)
    print_status 0 "Docker installed: $DOCKER_VERSION"
else
    print_status 1 "Docker not installed"
fi

if command -v docker-compose &> /dev/null; then
    COMPOSE_VERSION=$(docker-compose --version)
    print_status 0 "Docker Compose installed: $COMPOSE_VERSION"
else
    print_status 1 "Docker Compose not installed"
fi
echo ""

# 3. Validate docker-compose.yml syntax
echo "📝 Validating docker-compose.yml..."
if command -v docker-compose &> /dev/null; then
    if docker-compose config > /dev/null 2>&1; then
        print_status 0 "docker-compose.yml syntax is valid"
    else
        print_status 1 "docker-compose.yml has syntax errors"
        echo "   Run 'docker-compose config' to see details"
    fi
else
    print_warning "Cannot validate docker-compose.yml (docker-compose not installed)"
fi
echo ""

# 4. Check environment variables
echo "🔐 Checking Environment Variables..."
if [ -f "ENTRAZONE/.env" ]; then
    # Check critical variables
    grep -q "^SECRET_KEY=" ENTRAZONE/.env && print_status 0 "SECRET_KEY defined" || print_status 1 "SECRET_KEY missing"
    grep -q "^DB_NAME=" ENTRAZONE/.env && print_status 0 "DB_NAME defined" || print_status 1 "DB_NAME missing"
    grep -q "^DB_USER=" ENTRAZONE/.env && print_status 0 "DB_USER defined" || print_status 1 "DB_USER missing"
    grep -q "^DB_PASSWORD=" ENTRAZONE/.env && print_status 0 "DB_PASSWORD defined" || print_status 1 "DB_PASSWORD missing"
    
    # Check DB_HOST value
    DB_HOST=$(grep "^DB_HOST=" ENTRAZONE/.env | cut -d'=' -f2)
    if [ "$DB_HOST" = "db" ]; then
        print_status 0 "DB_HOST correctly set to 'db'"
    else
        print_status 1 "DB_HOST is '$DB_HOST' but should be 'db' for Docker"
    fi
    
    # Check DB_PORT
    grep -q "^DB_PORT=" ENTRAZONE/.env && print_status 0 "DB_PORT defined" || print_status 1 "DB_PORT missing"
    
    # Warn about default values
    if grep -q "SECRET_KEY=your-secret-key" ENTRAZONE/.env; then
        print_warning "SECRET_KEY appears to be using default value"
    fi
    
    if grep -q "DB_PASSWORD=changeme" ENTRAZONE/.env; then
        print_warning "DB_PASSWORD appears to be using default value"
    fi
else
    print_status 1 "ENTRAZONE/.env file not found"
fi
echo ""

# 5. Check port availability
echo "🔌 Checking Port Availability..."
if command -v lsof &> /dev/null; then
    if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 8000 is already in use"
    else
        print_status 0 "Port 8000 is available"
    fi
    
    if lsof -Pi :5432 -sTCP:LISTEN -t >/dev/null 2>&1; then
        print_warning "Port 5432 is already in use"
    else
        print_status 0 "Port 5432 is available"
    fi
else
    print_warning "Cannot check port availability (lsof not available)"
fi
echo ""

# 6. Check directory permissions
echo "📂 Checking Directory Permissions..."
[ -w "." ] && print_status 0 "Current directory is writable" || print_status 1 "Current directory is not writable"
[ -d "media" ] || mkdir -p media
[ -w "media" ] && print_status 0 "media/ directory is writable" || print_status 1 "media/ directory is not writable"
[ -d "static" ] || mkdir -p static
[ -w "static" ] && print_status 0 "static/ directory is writable" || print_status 1 "static/ directory is not writable"
echo ""

# 7. Summary
echo "📊 Validation Summary"
echo "===================================="
if [ $ERRORS -eq 0 ] && [ $WARNINGS -eq 0 ]; then
    echo -e "${GREEN}✅ All checks passed! Your Docker configuration is ready.${NC}"
    echo ""
    echo "Next steps:"
    echo "  1. docker-compose build"
    echo "  2. docker-compose up -d"
    echo "  3. docker-compose exec web python manage.py migrate"
    echo "  4. docker-compose exec web python manage.py createsuperuser"
elif [ $ERRORS -eq 0 ]; then
    echo -e "${YELLOW}⚠️  Configuration is valid but has $WARNINGS warning(s).${NC}"
    echo "Review warnings above before proceeding."
else
    echo -e "${RED}❌ Found $ERRORS error(s) and $WARNINGS warning(s).${NC}"
    echo "Please fix the errors above before running Docker."
    exit 1
fi
