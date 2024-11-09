import boto3
import time
import os

a=os.environ.get('AWS_ID')
b=os.environ.get('AWS_SEC')
print(a,b)

ec2 = boto3.client('ec2')
s3 = boto3.client('s3')

aws_access_ley=os.environ.get

user_data_script = f"""#!/bin/bash
apt update -y
apt install -y apache2
systemctl start apache2
systemctl enable apache2

# Install AWS CLI
sudo snap install aws-cli --classic

sudo aws configure set aws_access_key_id {a}
sudo aws configure set aws_secret_access_key {b}
sudo aws configure set default.region ap-south-1
sudo aws configure set default.output json

# Copy website files from S3 to EC2
sudo aws s3 cp s3://shauryatripathi22b/Website/ /var/www/html/ --recursive

# Log the output of the S3 copy command
sudo aws s3 cp s3://shauryatripathi22b/Website/ /var/www/html/ --recursive > /tmp/s3_copy_log.txt 2>&1

# Ensure proper permissions
chown -R www-data:www-data /var/www/html
chmod -R 755 /var/www/html
"""

def get_or_create_security_group():
    try:
        security_groups = ec2.describe_security_groups(GroupNames=['WebServerSG'])
        return security_groups['SecurityGroups'][0]['GroupId']
    except ec2.exceptions.ClientError:
        security_group = ec2.create_security_group(
            GroupName='WebServerSG',
            Description='Security group for web server with port 80 open'
        )
        
        # Add inbound rule to allow HTTP traffic
        ec2.authorize_security_group_ingress(
            GroupId=security_group['GroupId'],
            IpProtocol='tcp',
            FromPort=80,
            ToPort=80,
            CidrIp='0.0.0.0/0'
        )
        return security_group['GroupId']

# Get or create security group
security_group_id = get_or_create_security_group()

# Check if an instance with this security group already exists
instances = ec2.describe_instances(
    Filters=[
        {'Name': 'instance-state-name', 'Values': ['running', 'pending']},
        {'Name': 'instance.group-id', 'Values': [security_group_id]}
    ]
)

if instances['Reservations']:
    # Use existing instance
    instance_id = instances['Reservations'][0]['Instances'][0]['InstanceId']
    print(f"Using existing instance: {instance_id}")
else:
    response = ec2.run_instances(
        ImageId='ami-0522ab6e1ddcc7055',
        InstanceType='t2.micro',
        MinCount=1,
        MaxCount=1,
        UserData=user_data_script,
        SecurityGroupIds=[security_group_id],
        KeyName='test1'  # Replace with your key pair name
    )
    instance_id = response['Instances'][0]['InstanceId']
    print(f"Launched new instance: {instance_id}")

# Wait for the instance to be in 'running' state
while True:
    instances = ec2.describe_instances(InstanceIds=[instance_id])
    state = instances['Reservations'][0]['Instances'][0]['State']['Name']
    if state == 'running':
        break
    print("Instance is starting... waiting 10 seconds")
    time.sleep(10)

instances = ec2.describe_instances(InstanceIds=[instance_id])
public_dns = instances['Reservations'][0]['Instances'][0]['PublicDnsName']

print(f"Instance is now running. Public DNS: {public_dns}")
print("You can now open this DNS in a browser to verify if the static website works.")