# Setting Up Domain with Nginx Reverse Proxy

🚀 **Complete guide to exposing containerized applications on a custom domain using nginx reverse proxy with SSL**

---

## 📋 **Overview**

This guide documents the process of deploying a multi-container application (React frontend + Node.js backend) on AWS EC2 with a custom domain using nginx as a reverse proxy.

### **Architecture**
```
Internet → Route 53 → EC2 (Elastic IP) → Nginx (443/80) → Docker Containers
                                              ↓
                                         Frontend (8080)
                                         Backend (8040) via /api/
```

---

## 🌐 **Prerequisites**

- AWS Account with Route 53
- Domain name owned/transferred to AWS Route 53
- EC2 instance running Amazon Linux 2/2023
- Docker and Docker Compose installed
- Containerized application (frontend + backend)

---

## 🚀 **Step 1: AWS Infrastructure Setup**

### **1.1 EC2 Instance Setup**

```bash
# Launch EC2 instance with:
# - Amazon Linux 2023 AMI
# - t3.medium (or t3.small for testing)
# - 20 GB gp3 storage
```

### **1.2 Allocate Elastic IP**

1. **AWS Console** → **EC2** → **Elastic IPs** → **Allocate Elastic IP**
2. **Associate** with your EC2 instance
3. **Note the Elastic IP** (e.g., `54.227.220.5`)

### **1.3 Security Group Configuration**

```bash
# Inbound Rules Required:
Type: SSH     Port: 22    Source: YOUR_IP/32     (SSH access)
Type: HTTP    Port: 80    Source: 0.0.0.0/0     (HTTP redirect)
Type: HTTPS   Port: 443   Source: 0.0.0.0/0     (HTTPS access)

# Note: NO other ports should be exposed externally
```

---

## 🌐 **Step 2: DNS Configuration (Route 53)**

### **2.1 Create/Verify Hosted Zone**

```bash
# If domain was bought elsewhere, create hosted zone:
# Route 53 → Hosted zones → Create hosted zone
# Domain name: yourdomain.com
# Type: Public hosted zone
```

### **2.2 Create DNS Records**

**A Record (Root Domain):**
```
Record name: (blank)
Record type: A
Value: YOUR_ELASTIC_IP
TTL: 300
```

**CNAME Record (www subdomain):**
```
Record name: www
Record type: CNAME
Value: yourdomain.com
TTL: 300
```

### **2.3 Update Name Servers (if domain bought elsewhere)**

```bash
# Get AWS name servers from hosted zone:
ns-xxx.awsdns-xx.com
ns-xxx.awsdns-xx.net
ns-xxx.awsdns-xx.org
ns-xxx.awsdns-xx.co.uk

# Update at domain registrar (GoDaddy, Namecheap, etc.)
# Wait 15-30 minutes for propagation
```

---

## 🐳 **Step 3: Container Setup**

### **3.1 Docker Compose Configuration**

Create `docker-compose-production.yml`:

```yaml
version: '3.8'

services:
  frontend-service:
    image: your-registry/frontend:latest
    ports:
      - "127.0.0.1:8080:8080"  # Only bind to localhost
    depends_on:
      - backend-service
    restart: unless-stopped

  backend-service:
    image: your-registry/backend:latest
    ports:
      - "127.0.0.1:8040:8040"  # Only bind to localhost
    environment:
      - DEPLOYMENT_ENV=production
      - VITE_API_URL=/api
    restart: unless-stopped

volumes:
  app_data:
```

### **3.2 Frontend Configuration**

**Environment Variables in Dockerfile:**
```dockerfile
# Set production environment variables
ENV VITE_API_URL=/api
ENV VITE_PROFILE_API_URL=/api
ENV NODE_ENV=production
```

**API Configuration (src/config/api.ts):**
```typescript
export const config = {
  // Use /api prefix for nginx proxy in production
  URL: import.meta.env.VITE_API_URL || '/api',
  // ... other config
};
```

---

## 🔧 **Step 4: Server Setup Commands**

### **4.1 Install Required Software**

```bash
# Update system
sudo yum update -y

# Install Docker
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -a -G docker ec2-user

# Install Docker Compose
sudo curl -SL https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-linux-x86_64 -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install Nginx
sudo yum install -y nginx
sudo systemctl start nginx
sudo systemctl enable nginx

# Install Certbot for SSL
sudo yum install -y certbot python3-certbot-nginx
```

---

## 🔧 **Step 5: Nginx Configuration**

### **5.1 Create Domain Configuration**

```bash
# Create nginx configuration for your domain
sudo tee /etc/nginx/conf.d/yourdomain.com.conf > /dev/null <<'EOF'
server {
    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Document root for Let's Encrypt challenges
    root /var/www/html;
    index index.html;
    
    # Let's Encrypt ACME challenge directory
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }
    
    # Proxy to your frontend
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Proxy API calls to backend  
    location /api/ {
        proxy_pass http://localhost:8040/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
}
EOF
```

### **5.2 Prepare Web Root and Test Configuration**

```bash
# Create web root directory
sudo mkdir -p /var/www/html
sudo chown -R nginx:nginx /var/www/html

# Remove conflicting default configs
sudo rm -f /etc/nginx/conf.d/default.conf

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

---

## 🔒 **Step 6: SSL Certificate Setup**

### **6.1 Verify DNS and HTTP Access**

```bash
# Test DNS resolution
nslookup yourdomain.com

# Test HTTP access (should work before SSL)
curl -I http://yourdomain.com
```

### **6.2 Get SSL Certificate**

```bash
# Get Let's Encrypt SSL certificate
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Verify certificate auto-renewal
sudo certbot certificates
```

### **6.3 Final Nginx Configuration (Post-Certbot)**

After certbot, your configuration will look like:

```nginx
server {
    server_name yourdomain.com www.yourdomain.com;
    
    root /var/www/html;
    index index.html;
    
    location /.well-known/acme-challenge/ {
        root /var/www/html;
        try_files $uri =404;
    }
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /api/ {
        proxy_pass http://localhost:8040/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }

    listen 443 ssl; # managed by Certbot
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem; # managed by Certbot
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem; # managed by Certbot
    include /etc/letsencrypt/options-ssl-nginx.conf; # managed by Certbot
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem; # managed by Certbot
}

server {
    if ($host = www.yourdomain.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    if ($host = yourdomain.com) {
        return 301 https://$host$request_uri;
    } # managed by Certbot

    listen 80;
    server_name yourdomain.com www.yourdomain.com;
    return 404; # managed by Certbot
}
```

---

## 🚀 **Step 7: Application Deployment**

### **7.1 Deploy Containers**

```bash
# Start your application containers
docker-compose -f docker-compose-production.yml up -d

# Verify containers are running
docker ps

# Check container logs
docker-compose -f docker-compose-production.yml logs -f
```

### **7.2 Verify Local Container Access**

```bash
# Test frontend container locally
curl -I http://localhost:8080

# Test backend container locally  
curl -I http://localhost:8040

# Both should return HTTP 200 responses
```

---

## ✅ **Step 8: Testing and Verification**

### **8.1 DNS Testing**

```bash
# Test DNS resolution globally
nslookup yourdomain.com 8.8.8.8
nslookup yourdomain.com 1.1.1.1

# Should return your Elastic IP
```

### **8.2 HTTP/HTTPS Testing**

```bash
# Test HTTP redirect
curl -I http://yourdomain.com
# Should return: 301 redirect to HTTPS

# Test HTTPS access
curl -I https://yourdomain.com
# Should return: 200 OK

# Test API proxy
curl -I https://yourdomain.com/api/
# Should proxy to backend
```

### **8.3 Browser Testing**

1. **Open browser** → `https://yourdomain.com`
2. **Verify SSL certificate** (green lock icon)
3. **Check developer tools** for any errors
4. **Test application functionality**

---

## 🔧 **Useful Commands**

### **Nginx Management**

```bash
# Test configuration
sudo nginx -t

# Reload configuration
sudo systemctl reload nginx

# Restart nginx
sudo systemctl restart nginx

# Check status
sudo systemctl status nginx

# View configuration
sudo nginx -T
```

### **SSL Certificate Management**

```bash
# Check certificates
sudo certbot certificates

# Renew certificates (manual)
sudo certbot renew

# Test auto-renewal
sudo certbot renew --dry-run
```

### **Container Management**

```bash
# View running containers
docker ps

# Restart frontend container
docker-compose -f docker-compose-production.yml restart frontend-service

# View logs
docker-compose -f docker-compose-production.yml logs frontend-service

# Update and redeploy
docker-compose -f docker-compose-production.yml pull
docker-compose -f docker-compose-production.yml up -d
```

### **Debugging Commands**

```bash
# Check nginx error logs
sudo tail -f /var/log/nginx/error.log

# Check nginx access logs
sudo tail -f /var/log/nginx/access.log

# Test port connectivity
telnet yourdomain.com 443

# Check DNS propagation
dig yourdomain.com
```

---

## 🚨 **Common Issues and Solutions**

### **Issue 1: DNS Not Resolving**
```bash
# Solution: Check DNS propagation and name servers
nslookup yourdomain.com 8.8.8.8
# If fails: Update name servers at registrar
```

### **Issue 2: SSL Certificate Fails**
```bash
# Solution: Ensure HTTP works first
curl -I http://yourdomain.com
# Then run certbot again
```

### **Issue 3: White Screen / 404 Assets**
```bash
# Solution: Check container build and environment variables
docker exec -it container_name cat /usr/share/nginx/html/index.html
# Rebuild with correct VITE_API_URL=/api
```

### **Issue 4: API Calls Fail**
```bash
# Solution: Check nginx proxy configuration
sudo nginx -T | grep -A 10 "location /api"
# Ensure trailing slash in proxy_pass
```

---

## 🔒 **Security Best Practices**

1. **Only expose ports 80/443** - All container ports bound to localhost
2. **Use HTTPS everywhere** - HTTP redirects to HTTPS
3. **Regular SSL renewal** - Certbot auto-renewal configured
4. **Security headers** - Added in nginx configuration
5. **Firewall rules** - Restrict SSH access to your IP only

---

## 📋 **Quick Reference**

**Key Files:**
- Nginx config: `/etc/nginx/conf.d/yourdomain.com.conf`
- SSL certificates: `/etc/letsencrypt/live/yourdomain.com/`
- Container compose: `docker-compose-production.yml`

**Key Ports:**
- External: 80 (HTTP), 443 (HTTPS)
- Internal: 8080 (Frontend), 8040 (Backend)

**Key URLs:**
- Domain: `https://yourdomain.com`
- API Proxy: `https://yourdomain.com/api/`

---

*This setup provides a production-ready, secure deployment with SSL certificates, reverse proxy, and containerized applications.* 