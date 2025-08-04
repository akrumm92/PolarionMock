# Authentication Guide for PolarionMock

## Overview

PolarionMock uses JWT (JSON Web Token) based authentication to simulate Polarion's security model, while the real Polarion uses Personal Access Tokens (PAT). This guide explains the differences and how to configure authentication.

## Important: Polarion API Endpoints and Headers

### Polarion has two different API endpoints:

1. **Legacy API** (`/polarion/api`): 
   - Used for basic operations and authentication testing
   - Returns HTML responses (not JSON)
   - Works with standard headers

2. **REST API v1** (`/polarion/rest/v1`):
   - The main REST API for all operations
   - Returns JSON:API formatted responses
   - **REQUIRES Accept: `*/*` header** (not `application/json` or `application/vnd.api+json`)
   - Returns 406 "Not Acceptable" with other Accept headers

### Critical Header Requirements:

```python
# Correct headers for Polarion REST API v1
headers = {
    'Authorization': f'Bearer {pat}',
    'Accept': '*/*',  # MUST use wildcard!
    'Content-Type': 'application/json'
}
```

## Key Differences: Mock vs Production

### Production Polarion
- Uses **Personal Access Tokens (PAT)**
- Tokens are issued by Polarion directly
- No local verification needed
- Token stored in: `POLARION_PERSONAL_ACCESS_TOKEN`

### Mock Server
- Uses **JWT tokens** to simulate authentication
- Tokens are generated locally
- Verified using a secret key
- Token stored in: `MOCK_AUTH_TOKEN`
- Secret key stored in: `JWT_SECRET_KEY`

## Configuration

### Environment Variables

1. **DISABLE_AUTH** (in `.env`)
   - `true`: Disables authentication completely (useful for development)
   - `false`: Enables JWT authentication (default for production-like testing)

2. **JWT_SECRET_KEY** (in `.env`)
   - The secret key used to sign and verify JWT tokens in the mock
   - **Important**: This should be a secret string, NOT a JWT token itself
   - You can use any string you want (like a password)
   - Example: `JWT_SECRET_KEY=my-secret-password-123`
   - This is ONLY used by the mock server, not by real Polarion

3. **MOCK_AUTH_TOKEN** (in `.env`)
   - The JWT token used by tests when running against the mock
   - Generate this token using the `generate_token_auto.py` script

## Generating Tokens

### Automatic Token Generation

```bash
# Activate virtual environment
source venv/bin/activate

# Generate a token (valid for 24 hours)
python generate_token_auto.py
```

This will output:
- The JWT token
- Example curl commands to test the API

### Interactive Token Generation

```bash
python generate_token.py
```

This allows you to specify:
- User ID
- Username  
- Expiry time
- Custom permissions

## Using Tokens

### With curl

```bash
# Direct token in header
curl -H "Authorization: Bearer YOUR_TOKEN_HERE" http://localhost:5001/polarion/rest/v1/projects

# Using environment variable
export AUTH_TOKEN="Bearer YOUR_TOKEN_HERE"
curl -H "Authorization: $AUTH_TOKEN" http://localhost:5001/polarion/rest/v1/projects
```

### In Tests

Tests automatically use the token from `MOCK_AUTH_TOKEN` environment variable:

```python
# The auth_headers fixture in conftest.py handles this automatically
def test_list_projects(api_base_url, auth_headers):
    response = requests.get(f"{api_base_url}/projects", headers=auth_headers)
    assert response.status_code == 200
```

### For Production Tests

When testing against real Polarion:
- Set `POLARION_PERSONAL_ACCESS_TOKEN` in your `.env` file
- Tests will automatically use this token for production API calls

## Token Structure

JWT tokens contain:
- `user_id`: User identifier
- `username`: User display name
- `exp`: Expiration timestamp
- `iat`: Issued at timestamp
- `permissions`: Array of permissions (read, write, admin)

## Troubleshooting

### "Invalid token: Signature verification failed"

This error occurs when:
1. The JWT_SECRET_KEY in `.env` is incorrect (e.g., contains a token instead of a secret)
2. The token was generated with a different secret key
3. The mock server is still running with old configuration

Solution:
1. Check that `JWT_SECRET_KEY` contains a secret string, not a token
2. Restart the mock server: `pkill -f "python.*mock" && python -m src.mock`
3. Generate a new token with `python generate_token_auto.py`
4. Update `MOCK_AUTH_TOKEN` in `.env` with the new token

### Tests fail with 401 Unauthorized

1. Check if `DISABLE_AUTH=false` in `.env`
2. Ensure `MOCK_AUTH_TOKEN` is set to a valid token
3. Regenerate token if expired

### Tests pass but curl fails

Make sure you're using the correct token format:
- Correct: `Authorization: Bearer TOKEN`
- Wrong: `Authorization: TOKEN`
- Wrong: `Authorization: "Bearer TOKEN"` (no quotes needed)

## Security Best Practices

1. **Never commit real JWT secrets to git**
   - Use `.env` files (already in `.gitignore`)
   - Use different secrets for different environments

2. **Rotate tokens regularly**
   - Default expiry is 24 hours
   - Generate new tokens as needed

3. **Use strong secrets**
   - At least 32 characters
   - Mix of letters, numbers, and symbols
   - Different from any passwords

4. **Production vs Development**
   - Use `DISABLE_AUTH=true` only for local development
   - Always test with authentication enabled before deploying

## Simple Explanation

Think of it this way:
- **Real Polarion**: Uses Personal Access Tokens (like a key card issued by the building)
- **Mock Server**: Uses JWT tokens (like making your own temporary key cards for testing)
- **JWT_SECRET_KEY**: The machine that makes and checks the temporary key cards
- **MOCK_AUTH_TOKEN**: The actual temporary key card for testing

You need:
1. A `JWT_SECRET_KEY` (any password you choose) to make the mock authentication work
2. A `MOCK_AUTH_TOKEN` (generated using that secret) for the tests to authenticate