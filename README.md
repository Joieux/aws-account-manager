
# AWS Multi-Account Access Manager

A Python CLI tool for managing cross-account access in AWS using IAM roles and temporary credentials.

## Overview

This tool simplifies working with multiple AWS accounts by automating the process of assuming IAM roles and managing temporary credentials. Instead of manually switching between accounts in the AWS console or copying access keys, you can use simple commands to assume roles and automatically configure your AWS CLI profiles.

## Features

- **Account Management**: Configure and manage multiple AWS accounts in a single JSON file
- **Role Assumption**: Assume IAM roles across accounts with a single command
- **Credential Management**: Automatically save temporary credentials to AWS CLI profiles
- **Access Logging**: Track all role assumption attempts with timestamps and status
- **Error Handling**: Clear error messages with suggestions for common issues
- **Config Validation**: Validates account configuration to prevent errors

## Prerequisites

- Python 3.7 or higher
- AWS CLI configured with base credentials
- At least two AWS accounts (one main account and one or more target accounts)
- IAM roles set up with appropriate trust relationships

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/aws-account-manager.git
cd aws-account-manager
```

2. Install required dependencies:
```bash
pip3 install boto3
```

3. Ensure AWS CLI is configured:
```bash
aws configure
```

## Setup

### 1. Create Multiple AWS Accounts

If you don't already have multiple accounts, create them using AWS Organizations:

1. Log into your main AWS account
2. Navigate to AWS Organizations
3. Click "Create organization"
4. Add new accounts using "Add an AWS account" → "Create an AWS account"

### 2. Set Up Cross-Account IAM Roles

In each target account, create an IAM role that your main account can assume:

1. Go to IAM → Roles → Create role
2. Select "AWS account" as trusted entity
3. Enter your main account ID
4. Attach appropriate permissions (start with AdministratorAccess for testing)
5. Name the role (e.g., `CrossAccountAdminRole`)
6. Note the role ARN

### 3. Configure the Tool

On first run, the tool creates a default `accounts.json` file. Edit this file to add your accounts:

```json
{
  "accounts": [
    {
      "name": "main",
      "account_id": "123456789012",
      "description": "Main AWS Account"
    },
    {
      "name": "dev",
      "account_id": "987654321098",
      "role_arn": "arn:aws:iam::987654321098:role/CrossAccountAdminRole",
      "description": "Development Account"
    },
    {
      "name": "prod",
      "account_id": "555555555555",
      "role_arn": "arn:aws:iam::555555555555:role/CrossAccountAdminRole",
      "description": "Production Account"
    }
  ]
}
```

## Usage

### List All Configured Accounts

```bash
python3 account_manager.py list
```

Output:
```
Configured Accounts:
------------------------------------------------------------
Name: main
Account ID: 123456789012
Description: Main AWS Account
------------------------------------------------------------
Name: dev
Account ID: 987654321098
Description: Development Account
Role ARN: arn:aws:iam::987654321098:role/CrossAccountAdminRole
------------------------------------------------------------
```

### Check Current AWS Identity

```bash
python3 account_manager.py whoami
```

Output:
```
Current AWS Identity:
Account: 123456789012
User/Role ARN: arn:aws:iam::123456789012:user/cli-user
User ID: AIDAXXXXXXXXXXXXXXXXX
```

### Assume a Role in Another Account

```bash
python3 account_manager.py assume dev
```

Output:
```
Assuming role in dev account...
✓ Successfully assumed role!
Session expires at: 2025-10-06 22:04:06+00:00

✓ Created credentials profile: assumed-dev

To use this profile, run:
  export AWS_PROFILE=assumed-dev
Or add --profile assumed-dev to your AWS CLI commands
```

### Use the Assumed Role

After assuming a role, switch to that profile:

```bash
export AWS_PROFILE=assumed-dev
aws s3 ls
```

Or use it for a single command:

```bash
aws s3 ls --profile assumed-dev
```

### Switch Back to Main Account

```bash
unset AWS_PROFILE
```

## File Structure

```
aws-account-manager/
├── account_manager.py    # Main script
├── accounts.json         # Account configuration (created on first run)
├── access_log.txt       # Access attempt logs (created on first use)
├── README.md            # This file
└── requirements.txt     # Python dependencies
```

## How It Works

1. **Configuration**: The tool reads `accounts.json` to understand which accounts and roles are available
2. **Authentication**: Uses your configured AWS CLI credentials to authenticate with the main account
3. **Role Assumption**: Calls the STS `AssumeRole` API to get temporary credentials for the target account
4. **Credential Storage**: Saves the temporary credentials to `~/.aws/credentials` as a new profile
5. **Logging**: Records all access attempts in `access_log.txt` for audit purposes

## Security Considerations

- **Temporary Credentials**: All assumed role credentials are temporary and expire (default: 1 hour)
- **Audit Trail**: The `access_log.txt` file provides a record of all role assumptions
- **Least Privilege**: In production, replace AdministratorAccess with specific permissions needed
- **Credential Protection**: Never commit your `~/.aws/credentials` file or access keys to version control
- **Trust Relationships**: Only accounts explicitly listed in the role's trust policy can assume it

## Troubleshooting

### Error: ModuleNotFoundError: No module named 'boto3'

Install boto3:
```bash
pip3 install boto3
```

### Error: AccessDenied when assuming role

Check that:
- The trust relationship in the target account includes your main account ID
- Your user has `sts:AssumeRole` permission
- The role ARN in `accounts.json` is correct

### Error: Invalid principal in policy

Double-check the account ID in the trust relationship. AWS account IDs must be exactly 12 digits.

### Credentials not working after assuming role

Ensure you've exported the profile:
```bash
export AWS_PROFILE=assumed-dev
```

Verify it worked:
```bash
aws sts get-caller-identity
```

## Future Enhancements

Potential features for future versions:

- MFA support for role assumption
- Credential caching to reduce API calls
- Session duration configuration
- List and clean up expired profiles
- Support for external ID in trust relationships
- Integration with AWS SSO
- Automated role creation across accounts

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License - see LICENSE file for details

## Author

Built as a learning project to understand AWS IAM, cross-account access, and boto3.

## Resources

- [AWS IAM Roles Documentation](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html)
- [AWS STS AssumeRole API](https://docs.aws.amazon.com/STS/latest/APIReference/API_AssumeRole.html)
- [Boto3 Documentation](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
- [AWS Organizations](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_introduction.html)

## Blog Post

For a detailed walkthrough of building this tool, including challenges and lessons learned, check out the [blog post](link-to-your-blog).
