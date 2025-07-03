import { defineConfig } from 'vite'

export default defineConfig({
  // Development server configuration
  server: {
    port: 3000,
    host: true, // Allow external connections
    open: true, // Auto-open browser
    // Proxy API requests to Flask backend during development
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      // Also proxy direct routes that Flask handles
      '/dashboard': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      },
      '/docs': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false
      }
    }
  },
  
  // Build configuration for production
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    // Generate manifest for Flask to reference built assets
    manifest: true,
    rollupOptions: {
      input: {
        // Define entry points for your app
        dashboard: 'app/templates/dashboard.html',
        // Add other pages as needed
      }
    }
  },
  
  // Development source file locations
  root: '.', // Project root
  publicDir: 'app/static', // Static assets directory
  
  // CSS processing
  css: {
    devSourcemap: true
  }
})
