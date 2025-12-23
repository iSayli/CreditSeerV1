# CreditSeer - Sample Dashboard Deployment Guide

You can deploy the sample dashboard page as a standalone static website. The sample dashboard doesn't require any backend server or API calls - it's completely self-contained.

## Quick Deployment Options

### Option 1: Deploy Existing Files (Recommended)

The current `frontend/index.html` already has a working sample dashboard. Users just need to click the "View Sample Dashboard" button.

**Files needed:**
- `frontend/index.html`
- `frontend/styles.css`
- `frontend/CreditSeerLogo.svg`
- `frontend/assets/collapse_content.png`
- `frontend/assets/expand_content.png`

**Deploy these files to any static hosting service:**
- GitHub Pages
- Netlify
- Vercel
- AWS S3 + CloudFront
- Any web server (nginx, Apache, etc.)

### Option 2: Auto-Load Sample Dashboard

If you want the sample dashboard to load automatically (skip the upload page), you can add this script at the end of `index.html`:

```javascript
// Auto-load sample dashboard if URL has ?sample parameter
if (window.location.search.includes('?sample') || window.location.search.includes('&sample')) {
    window.addEventListener('load', () => {
        // Simulate clicking the "View Sample Dashboard" button
        setTimeout(() => {
            const viewSampleBtn = document.getElementById('viewSampleBtn');
            if (viewSampleBtn) {
                viewSampleBtn.click();
            }
        }, 100);
    });
}
```

Then access the page with: `https://your-domain.com/index.html?sample`

## Deployment Steps

### GitHub Pages

1. Push your code to a GitHub repository
2. Go to Settings → Pages
3. Select the branch and `/frontend` folder as the source
4. Your dashboard will be available at `https://yourusername.github.io/repository-name/index.html`

### Netlify

1. Install Netlify CLI: `npm install -g netlify-cli`
2. Navigate to the `frontend` folder: `cd frontend`
3. Deploy: `netlify deploy --prod`
4. Or drag and drop the `frontend` folder to [netlify.com/drop](https://app.netlify.com/drop)

### Vercel

1. Install Vercel CLI: `npm install -g vercel`
2. Navigate to the `frontend` folder: `cd frontend`
3. Deploy: `vercel --prod`

### AWS S3 Static Website

1. Create an S3 bucket
2. Enable static website hosting
3. Upload all files from the `frontend` folder
4. Set bucket policy to allow public read access
5. Access via the S3 website endpoint

## Important Notes

- **No Backend Required**: The sample dashboard works completely standalone
- **External Dependencies**: The page loads fonts and icons from:
  - Google Fonts (Inter, Archivo)
  - Material Icons (Google CDN)
  - Material Symbols (Google CDN)
- **API Calls**: The page makes one API call on load to reset server state, but it's wrapped in a try-catch and won't break if the API is unavailable
- **All Features Work**: Click-to-highlight, value editing, overrides, analyst notes - everything works in sample mode

## Testing Locally

You can test the deployment locally by serving the files with any static server:

```bash
# Python 3
cd frontend
python -m http.server 8000

# Node.js (if you have http-server installed)
cd frontend
npx http-server -p 8000

# PHP
cd frontend
php -S localhost:8000
```

Then visit: `http://localhost:8000/index.html` and click "View Sample Dashboard"

## File Structure

```
frontend/
├── index.html              # Main file (works standalone)
├── styles.css              # Required stylesheet
├── CreditSeerLogo.svg      # Logo image
└── assets/
    ├── collapse_content.png
    └── expand_content.png
```

All of these files are needed for the dashboard to display correctly.
