# Unison Platform Secrets

This directory contains sensitive configuration files for the Unison Platform.

## 🔐 Security Requirements

- **Permissions**: All files in this directory should have `600` permissions (read/write by owner only)
- **Directory**: This directory should have `700` permissions (read/write/execute by owner only)
- **Backup**: Never commit these files to version control
- **Sharing**: Only share with authorized personnel using secure channels

## 📁 Secret Files

### Database & Authentication
- `db_password.txt` - PostgreSQL database password
- `redis_password.txt` - Redis authentication password
- `admin_password.txt` - Admin interface password
- `jwt_signing_key.txt` - JWT token signing key (64 bytes base64)

### External Service Integration
- `paypal_client_secret.txt` - PayPal API client secret
- `figma_client_secret.txt` - Figma API client secret
- `venmo_client_secret.txt` - Venmo API client secret

### Infrastructure & Security
- `vault_token.txt` - Vault root token for initialization
- `aws_access_key.txt` - AWS access key for backups
- `aws_secret_key.txt` - AWS secret key for backups
- `session_secret.txt` - Session encryption secret

### Communication
- `smtp_password.txt` - Email service password
- `slack_webhook_url.txt` - Slack notifications webhook
- `analytics_api_key.txt` - Analytics service API key

## 🚀 Initialization

Run the security setup script to generate secure secrets:

```bash
sudo ./scripts/security-setup.sh
```

This script will:
1. Generate cryptographically secure random passwords
2. Set appropriate file permissions
3. Display generated passwords (save them securely)

## 📝 Template Files

Each secret should have a corresponding `.template` file with instructions:

```
# db_password.txt.template
# Generate with: openssl rand -base64 32
# Store securely in password manager
# Minimum 16 characters, include numbers and symbols
```

## 🔄 Rotation Schedule

### High Security (Quarterly)
- Database passwords
- JWT signing keys
- Vault tokens

### Medium Security (Semi-annually)
- External API secrets
- Session secrets

### Low Security (Annually)
- Admin passwords
- Notification webhooks

## 🛠️ Management Commands

### Generate new secret
```bash
# Generate 32-byte base64 encoded secret
openssl rand -base64 32 > secrets/new_secret.txt
chmod 600 secrets/new_secret.txt
```

### Verify secret permissions
```bash
# Check all secret files have correct permissions
find secrets/ -type f -not -perm 600
find secrets/ -type d -not -perm 700
```

### Audit secret access
```bash
# Monitor access to secret files
sudo auditctl -w /path/to/unison-platform/secrets/ -p rwxa -k unison_secrets
sudo ausearch -k unison_secrets
```

## 🚨 Emergency Procedures

### Compromise Response
1. Immediately rotate all secrets
2. Revoke all active sessions
3. Regenerate all API keys
4. Update all external service credentials
5. Review access logs for unauthorized access

### Secret Recovery
1. Check secure backup location
2. Contact system administrator
3. Use emergency recovery process
4. Document the incident

## 📋 Checklist

- [ ] All secret files have `600` permissions
- [ ] Secrets directory has `700` permissions
- [ ] No secrets committed to version control
- [ ] Backup procedure documented and tested
- [ ] Rotation schedule established
- [ ] Access logging enabled
- [ ] Emergency response plan prepared
- [ ] Team trained on secret management

## 🔍 Security Best Practices

1. **Never commit secrets to git**
2. **Use strong, unique passwords**
3. **Rotate secrets regularly**
4. **Limit access to authorized personnel**
5. **Use secure channels for sharing**
6. **Monitor access logs**
7. **Have backup and recovery procedures**
8. **Document all secret management processes**
