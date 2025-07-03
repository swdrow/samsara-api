# RowCast Development & Production Setup

## 🏗️ Project Structure

```
/samsara-api/
├── app/                    # Flask backend application
│   ├── static/            # Source static files (dev)
│   ├── templates/         # Jinja2 templates (dev)
│   └── ...
├── dist/                  # Built frontend assets (production)
├── .vscode/               # VS Code configuration
├── vite.config.js         # Vite frontend build configuration
├── package.json           # Frontend dependencies and scripts
├── dev_start.sh           # Development environment startup
├── prod_build.sh          # Production build script
└── start_server.sh        # Backend server startup
```

## 🚀 Development Environment

### Quick Start
```bash
# Start both frontend and backend servers
./dev_start.sh

# Or start them individually:
./dev_start.sh --frontend-only  # Frontend only (port 3000)
./dev_start.sh --backend-only   # Backend only (port 8000)
```

### What Happens in Development

1. **Frontend Dev Server (Vite - Port 3000)**
   - Serves your HTML, CSS, and JavaScript with hot reload
   - Automatically proxies API calls to the backend
   - Supports Builder.io Fusion for visual editing
   - Files served directly from `app/static/` and `app/templates/`

2. **Backend API Server (Flask - Port 8000)**
   - Serves only API endpoints (`/api/*`)
   - Does NOT serve static files in dev mode
   - Handles data processing and business logic

3. **Proxy Configuration**
   - Frontend requests to `/api/*` are automatically forwarded to Flask
   - Seamless development experience - frontend thinks it's all one server

### Development URLs
- **Frontend**: http://localhost:3000 (main development URL)
- **Backend API**: http://localhost:8000/api/* (direct API access)

## 📦 Production Deployment

### Build for Production
```bash
# Build and start production server
./prod_build.sh

# Or build frontend only
npm run build
```

### What Happens in Production

1. **Frontend Build Process**
   - Vite bundles all CSS, JavaScript, and assets
   - Outputs optimized files to `dist/` directory
   - Creates a manifest for cache-busting

2. **Single Server Deployment**
   - Flask serves both API endpoints AND the built frontend
   - Static files served from `dist/` instead of `app/static/`
   - No separate frontend server needed

3. **Production URLs**
   - **Everything**: http://localhost:8000 (single server for all content)

## 🔧 Configuration Details

### Vite Configuration (`vite.config.js`)
- **Development**: Proxies API requests to Flask backend
- **Build**: Outputs optimized bundles to `dist/`
- **Manifest**: Creates asset manifest for Flask integration

### Flask Configuration (`app/__init__.py`)
- **Development**: Uses `app/static/` and `app/templates/`
- **Production**: Uses `dist/` for all static content
- **Environment Detection**: Automatically switches based on `FLASK_ENV`

### Package.json Scripts
- `npm run dev`: Frontend dev server only
- `npm run api`: Backend server only  
- `npm run dev:full`: Both servers with concurrently
- `npm run build`: Build for production
- `npm run build:prod`: Build + start production server

## 🛠️ VS Code Integration

### Recommended Extensions
- Builder.io Fusion (already configured in `.vscode/extensions.json`)

### Available Tasks (Ctrl+Shift+P → "Tasks: Run Task")
- "Start Development Environment (Full)"
- "Start Frontend Dev Server Only"
- "Start Backend API Server Only"
- "Build for Production"
- "Build Frontend Only"

### Debug Configuration
- Launch configurations available in `.vscode/launch.json`
- Can debug both frontend and backend simultaneously

## 📋 Common Development Workflows

### 1. Full Stack Development
```bash
./dev_start.sh
# Visit http://localhost:3000
# Edit files in app/static/ or app/templates/
# Changes auto-reload in browser
```

### 2. Frontend Only (UI Development)
```bash
./dev_start.sh --frontend-only
# Backend API calls will fail, but UI development works
# Good for working on static designs
```

### 3. API Development Only
```bash
./dev_start.sh --backend-only
# Test API endpoints at http://localhost:8000/api/*
# No frontend hot reload
```

### 4. Production Testing
```bash
./prod_build.sh
# Test exactly how production will behave
# Single server at http://localhost:8000
```

## 🔄 Switching Between Development and Production

The system automatically detects the environment:

- **Development** (`FLASK_ENV=development`): Separate frontend/backend servers
- **Production** (`FLASK_ENV=production`): Single server serves both

No code changes needed - just use the appropriate startup script!

## 🏷️ Environment Variables

Copy `.env.example` to `.env.local` and customize:

```bash
# Frontend settings
VITE_DEV_PORT=3000
VITE_API_URL=http://localhost:8000

# Backend settings  
API_PORT=8000
FLASK_ENV=development  # or 'production'
```

## 🤝 Builder.io Fusion Integration

Builder.io Fusion works best with the frontend dev server:

1. Start development environment: `./dev_start.sh`
2. Open VS Code in this folder
3. Install Builder.io Fusion extension if prompted
4. Use the extension to visually edit your dashboard
5. Changes are saved to your actual template files
6. Hot reload shows changes instantly

The setup is now ready for visual webpage development with Builder.io Fusion!
