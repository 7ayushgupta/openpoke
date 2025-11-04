# Localhost Tunneling Guide

**Make your localhost app accessible online with a temporary public URL!**

Perfect for:
- Testing OAuth with real HTTPS URLs
- Sharing demos with others
- Testing on mobile devices
- Avoiding domain purchase for development

---

## 🚀 Quick Start: ngrok (Recommended)

### 1. Install ngrok

```bash
# macOS (Homebrew)
brew install ngrok

# Linux (snap)
sudo snap install ngrok

# Or download from: https://ngrok.com/download
```

### 2. Create Free Account

1. Go to https://ngrok.com/signup
2. Sign up (free tier is enough!)
3. Get your auth token from dashboard

### 3. Authenticate

```bash
ngrok config add-authtoken YOUR_AUTH_TOKEN
```

### 4. Start Your OpenPoke Backend

```bash
# Terminal 1: Start backend
python -m server.server
# Running on http://localhost:8001
```

### 5. Create Tunnel

```bash
# Terminal 2: Create tunnel
ngrok http 8001

# You'll see output like:
# Forwarding  https://abc123.ngrok.io -> http://localhost:8001
```

### 6. Update Environment Variables

```bash
# Get your ngrok URL (e.g., https://abc123.ngrok.io)
export OPENPOKE_CORS_ALLOW_ORIGINS=https://abc123.ngrok.io,http://localhost:3000
export OAUTH_REDIRECT_URI=https://abc123.ngrok.io/api/v1/auth/callback
export ENVIRONMENT=development  # Keep as development for now
```

### 7. Update Google OAuth Configuration

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. APIs & Services → Credentials
3. Your OAuth 2.0 Client
4. Add to "Authorized redirect URIs":
   ```
   https://abc123.ngrok.io/api/v1/auth/callback
   ```
5. Save

### 8. Start Your Frontend

```bash
# Terminal 3: Start frontend with ngrok URL
cd web
# Update your .env or set:
export NEXT_PUBLIC_API_BASE=https://abc123.ngrok.io
npm run dev
```

### 9. Access Your App!

**Option A: Via ngrok URL**
- Visit: `https://abc123.ngrok.io`
- Has HTTPS! ✅
- Can share with anyone! ✅

**Option B: Via localhost (for development)**
- Visit: `http://localhost:3000`
- Connects to ngrok backend

---

## 📱 Alternative: Cloudflare Tunnel (More Stable)

Cloudflare tunnels don't change URLs and work better for longer sessions.

### 1. Install Cloudflare Tunnel

```bash
# macOS
brew install cloudflare/cloudflare/cloudflared

# Linux
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

### 2. Login to Cloudflare

```bash
cloudflared tunnel login
```

### 3. Create a Tunnel

```bash
# Create tunnel
cloudflared tunnel create openpoke

# Note the tunnel ID shown
```

### 4. Create Configuration

Create `~/.cloudflared/config.yml`:

```yaml
tunnel: YOUR_TUNNEL_ID
credentials-file: /Users/yourusername/.cloudflared/YOUR_TUNNEL_ID.json

ingress:
  - hostname: your-subdomain.yourdomain.com
    service: http://localhost:8001
  - service: http_status:404
```

### 5. Create DNS Record

```bash
cloudflared tunnel route dns openpoke your-subdomain.yourdomain.com
```

### 6. Run the Tunnel

```bash
cloudflared tunnel run openpoke
```

**Note:** Cloudflare tunnel requires a domain, but you can use a free Cloudflare Pages domain.

---

## 🔧 Alternative: localtunnel (No Account Needed!)

Even simpler than ngrok - no account required!

### 1. Install

```bash
npm install -g localtunnel
```

### 2. Start Backend

```bash
python -m server.server
```

### 3. Create Tunnel

```bash
lt --port 8001 --subdomain myopenpoke

# You'll get: https://myopenpoke.loca.lt
# Note: Subdomain might not be available, will get random one
```

### 4. Update Configuration

Same as ngrok - update CORS and OAuth redirect URI.

**Limitations:**
- Less reliable than ngrok
- Random subdomains (unless you pay)
- Shows warning page on first visit

---

## ⚙️ Full Setup Example with ngrok

Here's a complete working setup:

### Terminal 1: Backend
```bash
cd /path/to/openpoke

# Set environment variables
export JWT_SECRET_KEY=$(python -c 'import secrets; print(secrets.token_urlsafe(32))')
export OPENPOKE_CORS_ALLOW_ORIGINS=https://abc123.ngrok.io,http://localhost:3000
export OAUTH_REDIRECT_URI=https://abc123.ngrok.io/api/v1/auth/callback
export ENVIRONMENT=development

# Start server
python -m server.server
```

### Terminal 2: ngrok Tunnel
```bash
ngrok http 8001 --log stdout

# Copy the HTTPS URL shown (e.g., https://abc123.ngrok.io)
```

### Terminal 3: Frontend
```bash
cd web

# Create .env.local
echo "NEXT_PUBLIC_API_BASE=https://abc123.ngrok.io" > .env.local

# Start frontend
npm run dev
```

### Browser
1. Visit `http://localhost:3000` OR `https://abc123.ngrok.io`
2. Login works with real OAuth!
3. HTTPS automatically handled by ngrok!

---

## 🔒 Security Considerations

### ✅ Safe for Development:
- Testing OAuth flows
- Sharing demos temporarily
- Testing on mobile devices
- Quick prototyping

### ⚠️ Not for Production:
- Tunnel URLs change frequently (ngrok free)
- Rate limits on free tiers
- Not as reliable as real hosting
- Tunnel service can see your traffic

### 🛡️ Best Practices:
1. **Don't expose real user data** through tunnels
2. **Use development/staging data only**
3. **Don't leave tunnels running 24/7**
4. **Upgrade to paid plan** for stable URLs if needed
5. **Never use for production** - buy a real domain!

---

## 📊 Comparison Table

| Service | Free Tier | Account Required | URL Stability | HTTPS | Best For |
|---------|-----------|------------------|---------------|-------|----------|
| **ngrok** | ✅ Yes | ✅ Yes | ⚠️ Changes | ✅ Auto | **Recommended** - Best balance |
| **Cloudflare** | ✅ Yes | ✅ Yes | ✅ Stable | ✅ Auto | Long-term dev, need stability |
| **localtunnel** | ✅ Yes | ❌ No | ❌ Random | ✅ Auto | Quick tests, no account |
| **Tailscale Funnel** | ✅ Yes | ✅ Yes | ✅ Stable | ✅ Auto | Private sharing |

---

## 🎯 Recommended Setup

For most developers, I recommend:

### Day-to-Day Development:
```bash
# Just use localhost - no tunnel needed
python -m server.server
cd web && npm run dev
# Visit: http://localhost:3000
```

### When You Need to Share/Test OAuth:
```bash
# Start ngrok tunnel
ngrok http 8001

# Update CORS and OAuth redirect URI
# Test and share!
```

### When Ready for Production:
```bash
# Buy a domain
# Deploy to real server
# Set up proper HTTPS
# See: docs/HTTPS_SETUP.md
```

---

## 🐛 Troubleshooting

### ngrok URL Changes Every Time
**Problem:** Free tier gets new random URL on each restart

**Solutions:**
1. **Pay for reserved domain** ($8/month) - keeps same URL
2. **Use Cloudflare Tunnel** - stable URLs
3. **Accept it** - just update OAuth redirect URI each time

### CORS Errors with Tunnel URL
**Problem:** Getting CORS errors when accessing via tunnel

**Solution:**
```bash
# Make sure tunnel URL is in CORS origins
export OPENPOKE_CORS_ALLOW_ORIGINS=https://your-tunnel-url.ngrok.io,http://localhost:3000

# Restart backend
python -m server.server
```

### OAuth Redirect Mismatch
**Problem:** "Redirect URI mismatch" error

**Solution:**
1. Check exact URL in error message
2. Go to Google Cloud Console
3. Add EXACT URL to authorized redirect URIs
4. Include the `/api/v1/auth/callback` path
5. Save and wait 5 minutes for propagation

### Tunnel Shows "Tunnel Not Found"
**Problem:** ngrok says tunnel doesn't exist

**Solution:**
```bash
# Re-authenticate
ngrok config add-authtoken YOUR_TOKEN

# Try again
ngrok http 8001
```

### Backend Can't Be Reached
**Problem:** ngrok tunnel up but backend returns 502

**Solution:**
```bash
# Make sure backend is actually running
curl http://localhost:8001/api/v1/health

# If not running, start it:
python -m server.server

# Then tunnel should work
```

---

## 💡 Pro Tips

### 1. Save ngrok Configuration
Create `~/.ngrok.yml`:
```yaml
version: "2"
authtoken: YOUR_AUTH_TOKEN
tunnels:
  openpoke:
    proto: http
    addr: 8001
    inspect: true
```

Then start with:
```bash
ngrok start openpoke
```

### 2. Use Custom Subdomain (Paid)
```bash
ngrok http 8001 --subdomain=myopenpoke
# Always get: https://myopenpoke.ngrok.io
```

### 3. Inspect Traffic
ngrok provides a web interface:
- Visit: http://localhost:4040
- See all HTTP requests/responses
- Great for debugging!

### 4. Multiple Tunnels
Run backend and frontend tunnels:
```bash
# Terminal 1: Backend tunnel
ngrok http 8001

# Terminal 2: Frontend tunnel  
ngrok http 3000

# Now you can share both!
```

### 5. Environment Switching Script
Create `start-with-tunnel.sh`:
```bash
#!/bin/bash

# Start ngrok in background
ngrok http 8001 --log=stdout > /tmp/ngrok.log &
sleep 2

# Extract URL
NGROK_URL=$(curl -s http://localhost:4040/api/tunnels | jq -r '.tunnels[0].public_url')
echo "Tunnel URL: $NGROK_URL"

# Set environment
export OPENPOKE_CORS_ALLOW_ORIGINS="$NGROK_URL,http://localhost:3000"
export OAUTH_REDIRECT_URI="$NGROK_URL/api/v1/auth/callback"

echo "Update OAuth redirect URI to: $NGROK_URL/api/v1/auth/callback"

# Start backend
python -m server.server
```

---

## 🎬 Quick Demo

**Want to show someone your app RIGHT NOW?**

```bash
# 1. Start backend (1 second)
python -m server.server &

# 2. Create tunnel (2 seconds)
ngrok http 8001

# 3. Share the HTTPS URL!
# "Check out my app: https://abc123.ngrok.io"
```

That's it! They can access your localhost app from anywhere! 🎉

---

## 📚 Additional Resources

- [ngrok Documentation](https://ngrok.com/docs)
- [Cloudflare Tunnel Docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-apps/)
- [localtunnel GitHub](https://github.com/localtunnel/localtunnel)

---

## Summary

**Can you make a public link?** ✅ Yes! Use ngrok  
**Is it free?** ✅ Yes (with limitations)  
**Does it have HTTPS?** ✅ Yes, automatic!  
**Setup time:** ⚡ 5 minutes  

**Perfect for:**
- Testing OAuth flows
- Mobile device testing  
- Quick demos
- Avoiding domain purchase

**Not for:**
- Production (use real domain + HTTPS)
- Permanent URLs (free tier changes)
- High traffic (rate limits)

**Next Steps:**
1. Install ngrok
2. Create tunnel: `ngrok http 8001`
3. Update CORS and OAuth with tunnel URL
4. Share and test!

When ready for real deployment → Buy domain + follow `HTTPS_SETUP.md`



