# Google OAuth Authentication Setup

This guide will help you set up Google OAuth authentication for Haven News.

## Step 1: Create Google OAuth Credentials

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select an existing one
3. Navigate to **APIs & Services** > **Credentials**
4. Click **Create Credentials** > **OAuth client ID**
5. Select **Web application** as the application type
6. Configure the OAuth consent screen if you haven't already
7. Add authorized redirect URIs:
   - Development: `http://localhost:8000/api/auth/google/callback`
   - Production: `https://your-domain.com/api/auth/google/callback`
8. Click **Create** and copy your **Client ID** and **Client Secret**

## Step 2: Configure Backend Environment Variables

1. Navigate to the `backend` directory
2. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

3. Update the following variables in your `.env` file:
   ```env
   # Google OAuth
   GOOGLE_CLIENT_ID=your-actual-google-client-id
   GOOGLE_CLIENT_SECRET=your-actual-google-client-secret

   # JWT Secret (generate a secure random string)
   JWT_SECRET_KEY=your-secure-random-string-here

   # Frontend URL (adjust for production)
   FRONTEND_URL=http://localhost:3000
   ```

## Step 3: Install Required Dependencies

Make sure you have the required Python packages installed:

```bash
cd backend
pip install -r requirements-dev.txt
```

Key dependencies for OAuth:
- `authlib` - OAuth library
- `python-jose[cryptography]` - JWT token handling
- `cryptography` - Cryptographic utilities

## Step 4: Configure Frontend Environment

1. Navigate to the `frontend` directory
2. Create `.env.local` file:
   ```bash
   cd frontend
   echo "NEXT_PUBLIC_API_URL=http://localhost:8000" > .env.local
   ```

## Step 5: Run the Application

1. Start the backend:
   ```bash
   cd backend
   python app.py
   ```

2. Start the frontend (in a new terminal):
   ```bash
   cd frontend
   npm run dev
   ```

## Step 6: Test the Authentication Flow

1. Navigate to `http://localhost:3000`
2. You should be redirected to the sign-in page
3. Click **Continue with Google**
4. Complete the Google OAuth flow
5. You'll be redirected back to the app with authentication

## File Structure

The authentication system includes:

### Backend Files
- `backend/auth.py` - OAuth configuration and JWT token management
- `backend/app.py` - Authentication endpoints (`/api/auth/*`)

### Frontend Files
- `frontend/app/sign-in/page.tsx` - Sign-in page component
- `frontend/services/auth.ts` - Authentication service (token management, API calls)
- `frontend/app/page.tsx` - Protected route with auth check

### Database
The User model in `backend/app.py` includes:
- OAuth provider information (Google)
- User profile data (email, name, avatar)
- User preferences and tickers
- Timestamps for tracking logins

## Authentication Flow

1. User clicks "Continue with Google" on `/sign-in` page
2. Frontend redirects to `GET /api/auth/google`
3. Backend initiates OAuth flow with Google
4. User authenticates with Google
5. Google redirects to `GET /api/auth/google/callback`
6. Backend creates/updates user in database
7. Backend generates JWT token
8. Backend redirects to frontend with token in URL
9. Frontend stores token in localStorage
10. Frontend makes authenticated requests with `Authorization: Bearer <token>` header

## API Endpoints

### Public Endpoints
- `GET /api/auth/google` - Initiate Google OAuth flow
- `GET /api/auth/google/callback` - Handle OAuth callback

### Protected Endpoints
- `GET /api/auth/me` - Get current user info (requires Bearer token)
- `POST /api/auth/logout` - Logout (clears token client-side)

## Security Notes

1. **Never commit** `.env` files to version control
2. Use strong, random strings for `JWT_SECRET_KEY`
3. In production:
   - Use HTTPS for all URLs
   - Set secure cookie flags
   - Implement CSRF protection
   - Add rate limiting to auth endpoints
4. Regularly rotate JWT secrets
5. Implement token refresh mechanism for long sessions

## Troubleshooting

### "Authentication Failed" Error
- Check that your Google OAuth credentials are correct
- Verify redirect URIs match exactly (including http/https)
- Check backend logs for detailed error messages

### Token Not Saved
- Check browser localStorage (DevTools > Application > Local Storage)
- Ensure `NEXT_PUBLIC_API_URL` matches your backend URL

### CORS Errors
- Verify frontend URL is in backend `cors_origins` list
- Check that credentials are enabled in CORS middleware

### OAuth Consent Screen Issues
- Complete all required fields in Google Cloud Console
- Add test users if app is in testing mode
- Ensure scopes match what's requested in code
