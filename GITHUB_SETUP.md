# GitHub Setup Instructions

## 1. Create GitHub Repo

Go to https://github.com/new and create a new repository:
- Name: `scansnap-organizer`
- Visibility: Private (recommended)
- No README, no .gitignore (we have those)

## 2. Connect and Push

Run these commands in the scansnap-app directory:

```bash
cd /home/node/.openclaw/workspace/scansnap-app

# Add remote (replace YOUR_USERNAME with your GitHub username)
git remote add origin https://github.com/YOUR_USERNAME/scansnap-organizer.git

# Push to GitHub
git branch -M main
git push -u origin main
```

## 3. Connect Streamlit Cloud

1. Go to https://streamlit.io/cloud
2. Sign in with GitHub
3. Click "New app"
4. Select your repo: `YOUR_USERNAME/scansnap-organizer`
5. Main file path: `streamlit_app.py`
6. Click "Deploy"

## 4. Add Secrets (Optional)

If you want password protection, add to Streamlit Cloud:
- Go to App Settings → Secrets
- Add:
  ```toml
  [auth]
  password = "your-secret-password"
  ```

Then modify streamlit_app.py to check the password.

## 5. Your App URL

After deployment, your app will be at:
`https://YOUR-APP-NAME.streamlit.app`

---

**Current status:**
- ✅ Git repo initialized
- ✅ 20 sample files in data/files.json
- ⚠️ Need to add remaining 149 files
- ⚠️ Need to push to GitHub
- ⚠️ Need to deploy to Streamlit Cloud
