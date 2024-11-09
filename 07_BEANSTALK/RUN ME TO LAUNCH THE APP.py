import boto3
from botocore.exceptions import ClientError
import os
import re
import subprocess
import sys

region='ap-south-1'
rds_client = boto3.client('rds', region_name=region)
environment_name = 'feedback-env2'
db_instance_identifier = 'feedback-db'

def create_rds_instance():
    """Create RDS instance"""
    try:
        print("Creating RDS instance...")
        response = rds_client.create_db_instance(
            DBInstanceIdentifier=db_instance_identifier,
            AllocatedStorage=20,
            DBInstanceClass='db.t4g.micro',
            Engine='mysql',
            MasterUsername='admin',
            MasterUserPassword='password', 
            DBName='feedback',
            PubliclyAccessible=True,
            BackupRetentionPeriod=7
        )
        
        print("Waiting for RDS instance to be available...")
        waiter = rds_client.get_waiter('db_instance_available')
        waiter.wait(DBInstanceIdentifier=db_instance_identifier)
        
        rds_info = rds_client.describe_db_instances(
            DBInstanceIdentifier=db_instance_identifier
        )
        return rds_info['DBInstances'][0]['Endpoint']['Address']
        
    except ClientError as e:
        if e.response['Error']['Code'] == 'DBInstanceAlreadyExists':
            print(f"RDS instance {db_instance_identifier} already exists.")
            rds_info = rds_client.describe_db_instances(
                DBInstanceIdentifier=db_instance_identifier
            )
            return rds_info['DBInstances'][0]['Endpoint']['Address']
        else:
            raise

# Create RDS instance--------------------------------------------------------------
print("Setting up RDS...")
rds_endpoint = create_rds_instance()
print(f"RDS endpoint: {rds_endpoint}")

# CREATING Database ---------------------------------------------------------------
def create_database(rds_endpoint):
    try:
        print("Creating feedback database in RDS instance...")
        # Run the MySQL command to create the database if it doesn't exist
        subprocess.run(
            ['mariadb', '-h', rds_endpoint, '-u', 'admin', '-ppassword','--ssl=FALSE'
             '-e', "\"CREATE DATABASE IF NOT EXISTS feedback;\""],
            check=True
        )
        print("Database created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error creating database: {e}")

# Update application.py with the RDS endpoint--------------------------------------
application_file_path = 'application.py'
with open(application_file_path, 'r') as file:
    file_contents = file.read()
new_file_contents = re.sub(
    r"'host': os\.environ\.get\('RDS_HOSTNAME', '.*?'\)",
    f"'host': os.environ.get('RDS_HOSTNAME', '{rds_endpoint}')",
    file_contents
)
with open(application_file_path, 'w') as file:
    file.write(new_file_contents)

# VERSIONING-----------------------------------------------------------------------
version_file_path = 'version.txt'
if os.path.exists(version_file_path):
    with open(version_file_path, 'r') as file:
        current_version = file.read().strip()
else:
    current_version = 'v0-0-0'
version_parts = current_version.lstrip('v').split('-')
version_parts = [int(part) for part in version_parts]
version_parts[-1] += 1
for i in range(len(version_parts) - 1, 0, -1):
    if version_parts[i] >= 10:
        version_parts[i] = 0
        version_parts[i - 1] += 1
new_version = 'v' + '-'.join(map(str, version_parts))
with open(version_file_path, 'w') as file:
    file.write(new_version)

print(f"Updated version: {new_version}")

with open('.elasticbeanstalk/config.yml', 'r') as file:
    config_contents = file.read()
new_config_contents = re.sub(
    r'(branch-defaults:\s+default:\s+environment:\s+)(\S+)',
    rf'\1{new_version}',
    config_contents
)
with open('.elasticbeanstalk/config.yml', 'w') as file:
    file.write(new_config_contents)


# launching the ELASTIC BEANSTALK APP----------------------------------------------
import subprocess

def run_eb_create():
    try:
        process = subprocess.Popen(
            ['eb', 'create', new_version],
            stdout=None,  
            stderr=None,  
            universal_newlines=True,
        )

        process.communicate()

        rc = process.returncode
        if rc != 0:
            raise subprocess.CalledProcessError(rc, process.args)

    except subprocess.CalledProcessError as e:
        print(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.")
    except KeyboardInterrupt:
        print("CREATING IN BACKGROUND")


print("Creating Elastic Beanstalk environment...")
run_eb_create()

subprocess.run(['eb', 'open'])

import subprocess

def terminate_environment():
    input("Press any key to terminate the environment...")

    try:
        process = subprocess.Popen(
            ['eb', 'terminate', '--force'],
            stdout=None,  
            stderr=None,  
            universal_newlines=True,
        )

        process.communicate()

        rc = process.returncode
        if rc != 0:
            raise subprocess.CalledProcessError(rc, process.args)

    except subprocess.CalledProcessError as e:
        print(f"Command '{e.cmd}' returned non-zero exit status {e.returncode}.")
    except KeyboardInterrupt:
        print("DELETING IN BACKGROUND")

terminate_environment()
