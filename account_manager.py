#!/usr/bin/env python3
"""
AWS Multi-Account Access Manager
Manages cross-account role assumption and credential management
"""

import boto3
import json
import os
from datetime import datetime
from pathlib import Path
from botocore.exceptions import ClientError, NoCredentialsError, ProfileNotFound

class ConfigError(Exception):
    """Custom exception for configuration errors"""
    pass

class AccountManager:
    def __init__(self, config_file='accounts.json'):
        self.config_file = config_file
        self.config = self.load_config()
        try:
            self.sts_client = boto3.client('sts')
        except NoCredentialsError:
            print("Error: AWS credentials not configured.")
            print("Run 'aws configure' to set up your credentials.")
            raise
        
    def load_config(self):
        """Load account configuration from JSON file"""
        if not os.path.exists(self.config_file):
            print(f"Config file {self.config_file} not found. Creating default...")
            self.create_default_config()
        
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
            
            self.validate_config(config)
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in config file: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Error loading config: {str(e)}")
    
    def validate_config(self, config):
        """Validate configuration structure"""
        if 'accounts' not in config:
            raise ConfigError("Config must contain 'accounts' key")
        
        if not isinstance(config['accounts'], list):
            raise ConfigError("'accounts' must be a list")
        
        for i, account in enumerate(config['accounts']):
            if 'name' not in account:
                raise ConfigError(f"Account at index {i} missing 'name' field")
            if 'account_id' not in account:
                raise ConfigError(f"Account '{account['name']}' missing 'account_id' field")
            
            # Validate account ID format (12 digits)
            if not account['account_id'].isdigit() or len(account['account_id']) != 12:
                raise ConfigError(f"Account '{account['name']}' has invalid account_id format")
    
    def create_default_config(self):
        """Create a default configuration file"""
        default_config = {
            "accounts": [
                {
                    "name": "main",
                    "account_id": "949396396071",
                    "description": "Main AWS Account"
                },
                {
                    "name": "dev",
                    "account_id": "093218045525",
                    "role_arn": "arn:aws:iam::093218045525:role/CrossAccountAdminRole",
                    "description": "Development Account"
                }
            ]
        }
        
        with open(self.config_file, 'w') as f:
            json.dump(default_config, f, indent=2)
        
        print(f"Created default config at {self.config_file}")
        print("Edit this file to add more accounts and roles")
    
    def list_accounts(self):
        """Display all configured accounts"""
        print("\nConfigured Accounts:")
        print("-" * 60)
        for account in self.config['accounts']:
            print(f"Name: {account['name']}")
            print(f"Account ID: {account['account_id']}")
            print(f"Description: {account.get('description', 'N/A')}")
            if 'role_arn' in account:
                print(f"Role ARN: {account['role_arn']}")
            print("-" * 60)
    
    def assume_role(self, account_name, session_name=None):
        """Assume a role in the specified account"""
        # Find the account in config
        account = None
        for acc in self.config['accounts']:
            if acc['name'] == account_name:
                account = acc
                break
        
        if not account:
            print(f"Error: Account '{account_name}' not found in config")
            print("\nAvailable accounts:")
            for acc in self.config['accounts']:
                print(f"  - {acc['name']}")
            return None
        
        if 'role_arn' not in account:
            print(f"Error: No role ARN configured for account '{account_name}'")
            print("Add a 'role_arn' field to this account in accounts.json")
            return None
        
        # Generate session name if not provided
        if not session_name:
            session_name = f"session-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
        
        try:
            print(f"\nAssuming role in {account_name} account...")
            response = self.sts_client.assume_role(
                RoleArn=account['role_arn'],
                RoleSessionName=session_name
            )
            
            credentials = response['Credentials']
            
            print(f"✓ Successfully assumed role!")
            print(f"Session expires at: {credentials['Expiration']}")
            
            # Log the access
            self.log_access(account_name, session_name, success=True)
            
            return credentials
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_msg = e.response['Error']['Message']
            
            print(f"✗ Error assuming role: {error_code}")
            print(f"Details: {error_msg}")
            
            if error_code == 'AccessDenied':
                print("\nPossible causes:")
                print("  - Trust relationship not configured correctly")
                print("  - Role doesn't exist in target account")
                print("  - Your user lacks sts:AssumeRole permission")
            
            self.log_access(account_name, session_name, success=False, error=error_msg)
            return None
            
        except Exception as e:
            print(f"✗ Unexpected error: {str(e)}")
            self.log_access(account_name, session_name, success=False, error=str(e))
            return None
    
    def save_credentials_to_profile(self, account_name, credentials, profile_name=None):
        """Save temporary credentials to AWS credentials file"""
        if not profile_name:
            profile_name = f"assumed-{account_name}"
        
        aws_dir = Path.home() / '.aws'
        credentials_file = aws_dir / 'credentials'
        
        # Ensure .aws directory exists
        aws_dir.mkdir(exist_ok=True)
        
        # Read existing credentials
        if credentials_file.exists():
            with open(credentials_file, 'r') as f:
                lines = f.readlines()
        else:
            lines = []
        
        # Remove old profile if it exists and clean up blank lines
        new_lines = []
        skip = False
        profile_found = False
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.strip() == f"[{profile_name}]":
                skip = True
                profile_found = True
                i += 1
                continue
            
            if skip and line.startswith('['):
                skip = False
            
            if not skip:
                # Skip excessive blank lines (more than one consecutive)
                if line.strip() == '':
                    if i + 1 < len(lines) and lines[i + 1].strip() == '':
                        i += 1
                        continue
                new_lines.append(line)
            
            i += 1
        
        # Add spacing before new profile if file has content
        if new_lines and new_lines[-1].strip() != '':
            new_lines.append('\n')
        
        # Add new credentials
        new_lines.append(f"[{profile_name}]\n")
        new_lines.append(f"aws_access_key_id = {credentials['AccessKeyId']}\n")
        new_lines.append(f"aws_secret_access_key = {credentials['SecretAccessKey']}\n")
        new_lines.append(f"aws_session_token = {credentials['SessionToken']}\n")
        
        # Write back
        try:
            with open(credentials_file, 'w') as f:
                f.writelines(new_lines)
            
            action = "Updated" if profile_found else "Created"
            print(f"\n✓ {action} credentials profile: {profile_name}")
            print(f"\nTo use this profile, run:")
            print(f"  export AWS_PROFILE={profile_name}")
            print(f"Or add --profile {profile_name} to your AWS CLI commands")
            
        except IOError as e:
            print(f"✗ Error writing credentials file: {str(e)}")
    
    def log_access(self, account_name, session_name, success=True, error=None):
        """Log access attempts to a file"""
        log_file = 'access_log.txt'
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        status = "SUCCESS" if success else "FAILED"
        log_entry = f"{timestamp} - {status} - Account: '{account_name}' - Session: {session_name}"
        
        if error:
            log_entry += f" - Error: {error}"
        
        try:
            with open(log_file, 'a') as f:
                f.write(log_entry + "\n")
        except IOError as e:
            print(f"Warning: Could not write to log file: {str(e)}")
    
    def get_current_identity(self):
        """Get current AWS identity information"""
        try:
            response = self.sts_client.get_caller_identity()
            print("\nCurrent AWS Identity:")
            print(f"Account: {response['Account']}")
            print(f"User/Role ARN: {response['Arn']}")
            print(f"User ID: {response['UserId']}")
            
        except ClientError as e:
            print(f"✗ Error getting identity: {e.response['Error']['Message']}")
        except NoCredentialsError:
            print("✗ No AWS credentials configured")
            print("Run 'aws configure' to set up your credentials")


def main():
    """Main CLI interface"""
    import sys
    
    try:
        manager = AccountManager()
    except (ConfigError, NoCredentialsError) as e:
        print(f"\n✗ Initialization failed: {str(e)}")
        return
    
    if len(sys.argv) < 2:
        print("AWS Multi-Account Access Manager")
        print("\nUsage:")
        print("  python3 account_manager.py list              - List all accounts")
        print("  python3 account_manager.py assume <account>  - Assume role in account")
        print("  python3 account_manager.py whoami            - Show current identity")
        print("\nExample:")
        print("  python3 account_manager.py assume dev")
        return
    
    command = sys.argv[1]
    
    if command == 'list':
        manager.list_accounts()
    
    elif command == 'assume':
        if len(sys.argv) < 3:
            print("Error: Please specify an account name")
            print("Usage: python3 account_manager.py assume <account>")
            return
        
        account_name = sys.argv[2]
        credentials = manager.assume_role(account_name)
        
        if credentials:
            manager.save_credentials_to_profile(account_name, credentials)
    
    elif command == 'whoami':
        manager.get_current_identity()
    
    else:
        print(f"Unknown command: {command}")
        print("Valid commands: list, assume, whoami")


if __name__ == '__main__':
    main()
