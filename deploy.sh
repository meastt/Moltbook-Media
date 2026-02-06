#!/bin/bash
# Molt Media Agent - Oracle Cloud Deployment Script

set -e  # Exit on error

echo "======================================"
echo "Molt Media Agent Deployment"
echo "======================================"

# Configuration
SSH_KEY="${SSH_KEY:-./id_rsa}"
SERVER_USER="${SERVER_USER:-ubuntu}"
SERVER_IP="${SERVER_IP}"

if [ -z "$SERVER_IP" ]; then
    echo "ERROR: SERVER_IP environment variable not set"
    echo "Usage: SERVER_IP=your.server.ip ./deploy.sh"
    exit 1
fi

SSH_CONN="${SERVER_USER}@${SERVER_IP}"
DEPLOY_DIR="/opt/molt-media"

echo "Deploying to: $SSH_CONN"
echo "Using SSH key: $SSH_KEY"
echo ""

# Test SSH connection
echo "Testing SSH connection..."
ssh -i "$SSH_KEY" -o StrictHostKeyChecking=no "$SSH_CONN" "echo 'SSH connection successful'"

# Create deployment directory on server
echo ""
echo "Creating deployment directory..."
ssh -i "$SSH_KEY" "$SSH_CONN" "sudo mkdir -p $DEPLOY_DIR && sudo chown -R $SERVER_USER:$SERVER_USER $DEPLOY_DIR"

# Copy files to server
echo ""
echo "Copying files to server..."
rsync -avz --progress -e "ssh -i $SSH_KEY" \
    --exclude '.git' \
    --exclude '.env.example' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.DS_Store' \
    --exclude 'venv' \
    --exclude 'molt-media-*.tar.gz' \
    ./ "$SSH_CONN:$DEPLOY_DIR/"

# Copy .env file separately (secure)
echo ""
echo "Copying .env file..."
scp -i "$SSH_KEY" .env "$SSH_CONN:$DEPLOY_DIR/.env"
ssh -i "$SSH_KEY" "$SSH_CONN" "chmod 600 $DEPLOY_DIR/.env"

# Install dependencies and set up service
echo ""
echo "Installing dependencies on server..."
ssh -i "$SSH_KEY" "$SSH_CONN" << 'ENDSSH'
set -e

# Install Python and dependencies
if command -v apt &> /dev/null; then
    sudo apt update
    sudo apt install -y python3 python3-pip jq curl
elif command -v dnf &> /dev/null; then
    sudo dnf check-update || true
    sudo dnf install -y python3 python3-pip jq curl
elif command -v yum &> /dev/null; then
    sudo yum check-update || true
    sudo yum install -y python3 python3-pip jq curl
else
    echo "Error: innovative package manager not found"
    exit 1
fi

# Install Python packages
cd /opt/molt-media
pip3 install -r requirements.txt --user

# Create molt-media user if it doesn't exist
if ! id "molt-media" &>/dev/null; then
    sudo useradd -r -s /bin/false molt-media
    echo "Created molt-media user"
fi

# Set permissions
sudo chown -R molt-media:molt-media /opt/molt-media

# Create log directory
sudo mkdir -p /var/log/molt-media
sudo chown molt-media:molt-media /var/log/molt-media

# Install systemd service
sudo cp /opt/molt-media/molt-media.service /etc/systemd/system/
sudo systemctl daemon-reload

echo ""
echo "Setup complete on server!"
ENDSSH

# Start the service
echo ""
echo "Starting Molt Media service..."
ssh -i "$SSH_KEY" "$SSH_CONN" << 'ENDSSH'
sudo systemctl enable molt-media
sudo systemctl restart molt-media
sudo systemctl status molt-media --no-pager
ENDSSH

echo ""
echo "======================================"
echo "Deployment Complete!"
echo "======================================"
echo ""
echo "Monitor logs with:"
echo "  ssh -i $SSH_KEY $SSH_CONN 'sudo journalctl -u molt-media -f'"
echo ""
echo "Check status with:"
echo "  ssh -i $SSH_KEY $SSH_CONN 'sudo systemctl status molt-media'"
echo ""
echo "View activity log:"
echo "  ssh -i $SSH_KEY $SSH_CONN 'cat $DEPLOY_DIR/memory/activity-log.md'"
echo ""
