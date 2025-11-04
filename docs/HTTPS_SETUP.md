# HTTPS Setup Guide

This guide shows you how to set up HTTPS/TLS for OpenPoke in production.

**⚠️ HTTPS is CRITICAL for production - do not skip this step!**

---

## Why HTTPS is Required

Without HTTPS:
- JWT tokens can be intercepted (session hijacking)
- OAuth codes can be stolen (account takeover)
- All user data transmitted in plaintext
- Man-in-the-middle attacks are trivial

**Cost of not using HTTPS: Complete system compromise**

---

## Recommended Approach: Reverse Proxy

The best practice is to use a reverse proxy (nginx or Caddy) to handle HTTPS:

```
Internet → [Reverse Proxy with TLS] → [OpenPoke on localhost:8001]
         ↓
    Handles HTTPS
    Terminates TLS
    Sets security headers
```

---

## Option 1: Caddy (Easiest - Automatic HTTPS)

Caddy automatically obtains and renews Let's Encrypt certificates.

### 1. Install Caddy

```bash
# Ubuntu/Debian:
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy

# macOS:
brew install caddy
```

### 2. Create Caddyfile

Create `/etc/caddy/Caddyfile`:

```caddy
# Replace with your actual domain
yourdomain.com {
    # Reverse proxy to OpenPoke backend
    reverse_proxy localhost:8001 {
        # Pass real client IP
        header_up X-Real-IP {remote_host}
        header_up X-Forwarded-For {remote_host}
        header_up X-Forwarded-Proto {scheme}
    }
    
    # Security headers
    header {
        # Prevent clickjacking
        X-Frame-Options "DENY"
        
        # Prevent MIME sniffing
        X-Content-Type-Options "nosniff"
        
        # Enable XSS protection
        X-XSS-Protection "1; mode=block"
        
        # Force HTTPS
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        
        # Control referrer information
        Referrer-Policy "strict-origin-when-cross-origin"
        
        # Content Security Policy (adjust as needed)
        # Content-Security-Policy "default-src 'self'"
        
        # Remove server header
        -Server
    }
    
    # Enable compression
    encode gzip
    
    # Logging
    log {
        output file /var/log/caddy/openpoke.log
        format json
    }
}

# Optionally handle www subdomain
www.yourdomain.com {
    redir https://yourdomain.com{uri} permanent
}
```

### 3. Start Caddy

```bash
# Test configuration
sudo caddy validate --config /etc/caddy/Caddyfile

# Start Caddy
sudo systemctl enable caddy
sudo systemctl start caddy

# Check status
sudo systemctl status caddy

# View logs
sudo journalctl -u caddy -f
```

### 4. Done!

Caddy automatically:
- ✅ Obtains Let's Encrypt certificate
- ✅ Renews certificates before expiration
- ✅ Redirects HTTP to HTTPS
- ✅ Serves your application over HTTPS

---

## Option 2: Nginx (More Control)

Nginx requires manual Let's Encrypt setup but offers more configuration options.

### 1. Install Nginx and Certbot

```bash
# Ubuntu/Debian:
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx

# macOS:
brew install nginx certbot
```

### 2. Create Nginx Configuration

Create `/etc/nginx/sites-available/openpoke`:

```nginx
# HTTP server - redirects to HTTPS
server {
    listen 80;
    listen [::]:80;
    server_name yourdomain.com www.yourdomain.com;
    
    # Let's Encrypt challenge
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }
    
    # Redirect everything else to HTTPS
    location / {
        return 301 https://$server_name$request_uri;
    }
}

# HTTPS server
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name yourdomain.com;
    
    # SSL certificates (will be created by certbot)
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers 'ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384';
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 10m;
    
    # OCSP stapling
    ssl_stapling on;
    ssl_stapling_verify on;
    ssl_trusted_certificate /etc/letsencrypt/live/yourdomain.com/chain.pem;
    resolver 8.8.8.8 8.8.4.4 valid=300s;
    resolver_timeout 5s;
    
    # Security headers
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains; preload" always;
    add_header X-Frame-Options "DENY" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    
    # Remove server header
    server_tokens off;
    
    # Proxy to OpenPoke backend
    location / {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        
        # Pass headers
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # WebSocket support (if needed)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
    
    # Logging
    access_log /var/log/nginx/openpoke-access.log;
    error_log /var/log/nginx/openpoke-error.log;
}

# Redirect www to non-www
server {
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name www.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    return 301 https://yourdomain.com$request_uri;
}
```

### 3. Enable Configuration

```bash
# Create symlink
sudo ln -s /etc/nginx/sites-available/openpoke /etc/nginx/sites-enabled/

# Test configuration
sudo nginx -t

# Don't reload yet - need certificate first!
```

### 4. Obtain Let's Encrypt Certificate

```bash
# Stop nginx temporarily
sudo systemctl stop nginx

# Obtain certificate
sudo certbot certonly --standalone -d yourdomain.com -d www.yourdomain.com

# Or if nginx is running:
sudo certbot --nginx -d yourdomain.com -d www.yourdomain.com

# Start nginx
sudo systemctl start nginx
sudo systemctl enable nginx
```

### 5. Auto-Renewal

```bash
# Test renewal
sudo certbot renew --dry-run

# Certbot automatically adds a cron job for renewal
# Check with:
sudo systemctl list-timers | grep certbot
```

---

## Option 3: Cloud Load Balancer

If deploying to cloud, use the cloud provider's load balancer for HTTPS:

### AWS (Application Load Balancer)
1. Create ALB in AWS Console
2. Add HTTPS listener with ACM certificate
3. Forward to OpenPoke backend
4. Set `X-Forwarded-Proto` header

### Google Cloud (Cloud Load Balancing)
1. Create HTTPS load balancer
2. Add managed certificate
3. Backend points to OpenPoke
4. Headers automatically set

### Azure (Application Gateway)
1. Create Application Gateway
2. Add TLS certificate
3. Backend pool with OpenPoke
4. Configure health probes

---

## Verification

After setting up HTTPS, verify it works:

### 1. Check HTTPS is Working
```bash
# Should return 200 with HTTPS:
curl -I https://yourdomain.com/api/v1/health

# HTTP should redirect to HTTPS:
curl -I http://yourdomain.com/api/v1/health
# Should see 301 redirect
```

### 2. Test Security Headers
```bash
curl -I https://yourdomain.com | grep -i "strict-transport"
# Should see: Strict-Transport-Security: max-age=...
```

### 3. Check SSL Quality
Visit: https://www.ssllabs.com/ssltest/analyze.html?d=yourdomain.com

Aim for **A+ rating**.

### 4. Test Your App
- Visit https://yourdomain.com
- Login should work
- Check browser console for errors
- Verify no mixed content warnings

---

## Environment Variables for Production

After setting up HTTPS, update your environment:

```bash
# Set production mode
export ENVIRONMENT=production

# Update CORS for HTTPS
export OPENPOKE_CORS_ALLOW_ORIGINS=https://yourdomain.com

# Update OAuth redirect URI
export OAUTH_REDIRECT_URI=https://yourdomain.com/api/v1/auth/callback

# Update in Google Cloud Console too!
# OAuth → Credentials → Authorized redirect URIs
```

---

## Troubleshooting

### Certificate Not Working
```bash
# Check certificate expiration
sudo certbot certificates

# Renew manually
sudo certbot renew

# Check nginx/caddy logs
sudo tail -f /var/log/nginx/error.log
sudo journalctl -u caddy -f
```

### Mixed Content Errors
- Ensure all resources loaded via HTTPS
- Check browser console for warnings
- Update any hardcoded HTTP URLs to HTTPS

### CORS Errors After HTTPS
- Update `OPENPOKE_CORS_ALLOW_ORIGINS` to use `https://`
- Restart OpenPoke backend
- Clear browser cache

### OAuth Redirect Mismatch
- Update redirect URI in Google Cloud Console
- Must exactly match `OAUTH_REDIRECT_URI` environment variable
- Include https:// prefix

---

## Cost

### Let's Encrypt (Caddy/Nginx)
- **Cost:** FREE
- **Renewal:** Automatic
- **Trusted:** All browsers

### Cloud Provider Certificates
- **AWS ACM:** FREE for ALB/CloudFront
- **Google Cloud:** FREE managed certificates
- **Azure:** Varies by service

---

## Next Steps

After HTTPS is working:

1. ✅ Verify with SSL Labs
2. ✅ Update OAuth redirect URIs
3. ✅ Update CORS configuration
4. ✅ Test login flow end-to-end
5. ✅ Monitor certificate expiration
6. ✅ Set up alerts for renewal failures

---

## Quick Start: Caddy One-Liner

For the absolute fastest HTTPS setup:

```bash
# Install Caddy
curl https://getcaddy.com | bash -s personal

# Create Caddyfile
echo "yourdomain.com { reverse_proxy localhost:8001 }" > Caddyfile

# Run (automatic HTTPS!)
sudo caddy run

# That's it! 🎉
```

---

**Remember: HTTPS is NOT optional for production. It's a critical security requirement!**

