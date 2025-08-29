# Authentication System Documentation

## Overview

The AI Travel Planner now includes a comprehensive authentication system with role-based access control (RBAC) to secure user data and provide administrative capabilities.

## Features

### 🔐 **User Authentication**
- **Google OAuth Integration**: Secure login using Google accounts
- **Session Management**: Persistent login sessions with secure cookies
- **Automatic User Creation**: New users are automatically created upon first login

### 👥 **Role-Based Access Control**
- **User Roles**: Three distinct user roles with different permissions
- **Plan Ownership**: Users can only access their own saved plans
- **Admin Override**: Admins and root users can access all plans

### 🛡️ **Security Features**
- **Route Protection**: Authentication decorators protect sensitive endpoints
- **Access Control**: Users cannot access other users' plans
- **Admin Panel**: Secure admin interface for user management

## User Roles

### 1. **Regular User** (`user`)
- Can create and save their own travel plans
- Can view, edit, and delete only their own plans
- Cannot access other users' data
- Cannot access admin features

### 2. **Admin** (`admin`)
- All regular user permissions
- Can view all users' travel plans
- Can edit and delete any plan
- Can access admin panel for user management
- Cannot modify user roles

### 3. **Root** (`root`)
- All admin permissions
- Can modify user roles (promote/demote users)
- Full system access
- Can manage all aspects of the application

## Database Schema

### Users Table
```sql
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    google_id TEXT UNIQUE,
    email TEXT UNIQUE NOT NULL,
    name TEXT,
    picture TEXT,
    role TEXT DEFAULT 'user',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Trips Table (Updated)
```sql
CREATE TABLE trips (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    unique_id TEXT UNIQUE NOT NULL,
    user_id INTEGER,  -- Foreign key to users table
    -- ... other fields ...
    FOREIGN KEY (user_id) REFERENCES users (id)
);
```

## API Endpoints

### Authentication Endpoints
- `GET /auth/google/login` - Initiate Google OAuth login
- `GET /auth/google/callback` - Handle OAuth callback
- `GET /auth/google/logout` - Logout user
- `GET /api/user/is-authenticated` - Check authentication status
- `GET /api/user/profile` - Get current user profile

### Protected Plan Endpoints
- `GET /api/plans` - List saved plans (user's own or all for admins)
- `GET /api/plans/<plan_id>` - Get specific plan (with access control)
- `POST /api/save` - Save new plan (requires authentication)
- `PUT /api/plans/<plan_id>` - Update plan (owner or admin only)
- `DELETE /api/plans/<plan_id>` - Delete plan (owner or admin only)

### Admin Endpoints
- `GET /admin` - Admin panel page (admin/root only)
- `GET /api/admin/users` - List all users (admin/root only)
- `PUT /api/admin/users/<user_id>/role` - Update user role (root only)
- `GET /api/admin/stats` - Get system statistics (admin/root only)

## Authentication Decorators

### `@login_required`
- Ensures user is authenticated
- Returns 401 if not logged in

### `@admin_required`
- Ensures user has admin or root role
- Returns 403 if insufficient permissions

### `@root_required`
- Ensures user has root role
- Returns 403 if insufficient permissions

## Setup Instructions

### 1. **Environment Variables**
Add these to your `.env` file:
```env
SECRET_KEY=your-secret-key-here
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
```

### 2. **Google OAuth Setup**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add `http://localhost:5000/auth/google/callback` to authorized redirect URIs
6. Copy Client ID and Client Secret to your `.env` file

### 3. **Database Initialization**
The system automatically creates the necessary tables and a default admin user:
- Email: `admin@travelplanner.com`
- Role: `root`

### 4. **Admin User Setup**
To create additional admin users:
1. Login with the Google account you want to make admin
2. Access the admin panel (if you have root access)
3. Change the user's role to `admin` or `root`

## Usage Examples

### Frontend Authentication Check
```javascript
// Check if user is authenticated
const response = await fetch('/api/user/is-authenticated');
const data = await response.json();

if (data.authenticated) {
    console.log('User:', data.user);
    console.log('Role:', data.user.role);
} else {
    console.log('User not authenticated');
}
```

### Protected API Calls
```javascript
// Save a plan (requires authentication)
const response = await fetch('/api/save', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(planData)
});

if (response.status === 401) {
    // User not authenticated
    showLoginPrompt();
} else if (response.status === 403) {
    // Access denied
    showAccessDenied();
}
```

## Security Considerations

### 1. **Session Security**
- Sessions use secure cookies
- Session data is stored server-side
- Automatic session expiration

### 2. **Access Control**
- All plan operations check user ownership
- Admin operations require appropriate role
- Database queries filter by user_id

### 3. **Input Validation**
- All user inputs are validated
- SQL injection protection through parameterized queries
- XSS protection through proper output encoding

### 4. **Error Handling**
- Authentication errors return appropriate HTTP status codes
- Sensitive information is not exposed in error messages
- Graceful fallbacks for authentication failures

## Troubleshooting

### Common Issues

1. **"Google OAuth not available"**
   - Ensure Google OAuth libraries are installed
   - Check environment variables are set correctly

2. **"Authentication required" errors**
   - User needs to login via Google OAuth
   - Check if session cookies are enabled

3. **"Access denied" errors**
   - User doesn't have sufficient permissions
   - Check user role in admin panel

4. **Admin panel not accessible**
   - Ensure user has admin or root role
   - Check if admin route is properly protected

### Debug Mode
Enable debug logging by setting:
```python
app.debug = True
```

## Future Enhancements

1. **Password-based Authentication**: Add traditional username/password login
2. **Two-Factor Authentication**: Add 2FA for additional security
3. **API Tokens**: Add API key authentication for external integrations
4. **Audit Logging**: Track user actions for security monitoring
5. **Rate Limiting**: Prevent abuse through rate limiting
6. **Email Verification**: Require email verification for new accounts

## Support

For issues related to the authentication system:
1. Check the logs for error messages
2. Verify environment variables are set correctly
3. Ensure Google OAuth is properly configured
4. Check database connectivity and schema
