import boto3
from botocore.exceptions import ClientError
import time

ec2_client = boto3.client('ec2', region_name='ap-south-1')
rds_client = boto3.client('rds', region_name='ap-south-1')

# Define EC2 and RDS configurations
ec2_instance_type = 't2.micro' 
ami_id = 'ami-0dee22c13ea7a9a67'
key_name = 'test1'  
security_group_name = 'ec2_rds_'
db_instance_identifier = 'feedback'
db_instance_class = 'db.t4g.micro' 
db_engine = 'mysql'
db_name = 'feedback'
db_master_username = 'admin'
db_master_password = 'password'

# Create or retrieve security group
try:
    response = ec2_client.create_security_group(
        GroupName=security_group_name,
        Description='Security group for EC2 and RDS communication'
    )
    security_group_id = response['GroupId']
    
    # Add ingress rules for MySQL (port 3306) and HTTP (port 80)
    ec2_client.authorize_security_group_ingress(
        GroupId=security_group_id,
        IpPermissions=[
            {
                'IpProtocol': 'tcp',
                'FromPort': 3306,
                'ToPort': 3306,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 22,
                'ToPort': 22,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            },
            {
                'IpProtocol': 'tcp',
                'FromPort': 80,
                'ToPort': 80,
                'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
            }
        ]
    )
    print(f"Created security group: {security_group_id}")
except ClientError as e:
    if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
        response = ec2_client.describe_security_groups(GroupNames=[security_group_name])
        security_group_id = response['SecurityGroups'][0]['GroupId']
        print(f"Using existing security group: {security_group_id}")
    else:
        print(f"Error creating security group: {e}")
        raise

try:
    rds_instance = rds_client.create_db_instance(
        DBInstanceIdentifier=db_instance_identifier,
        AllocatedStorage=20,
        DBInstanceClass=db_instance_class,
        Engine=db_engine,
        MasterUsername=db_master_username,
        MasterUserPassword=db_master_password,
        DBName=db_name,
        VpcSecurityGroupIds=[security_group_id],
        PubliclyAccessible=True, 
        BackupRetentionPeriod=7  
    )
    print(f"RDS instance {db_instance_identifier} is being created...")
    
    # Wait for the RDS instance to be available
    waiter = rds_client.get_waiter('db_instance_available')
    waiter.wait(DBInstanceIdentifier=db_instance_identifier)
    print(f"RDS instance {db_instance_identifier} is available.")
except ClientError as e:
    if e.response['Error']['Code'] == 'DBInstanceAlreadyExists':
        print(f"RDS instance {db_instance_identifier} already exists.")
    else:
        print(f"Error creating RDS instance: {e}")
        raise

try:
    rds_info = rds_client.describe_db_instances(DBInstanceIdentifier=db_instance_identifier)
    rds_endpoint = rds_info['DBInstances'][0]['Endpoint']['Address']
    print(f"RDS endpoint: {rds_endpoint}")
except ClientError as e:
    print(f"Error retrieving RDS endpoint: {e}")
    raise

# Read and update the user data script
try:
    with open('userdata_d.txt', 'r') as file:
        user_data = file.read()
    user_data = user_data.replace('feedback.cniuq0gcmxho.ap-south-1.rds.amazonaws.com', rds_endpoint)
except IOError as e:
    print(f"Error reading userdata.txt: {e}")
    raise

try:
    ec2_instance = ec2_client.run_instances(
        ImageId=ami_id,
        InstanceType=ec2_instance_type,
        KeyName=key_name,
        MinCount=1,
        MaxCount=1,
        SecurityGroupIds=[security_group_id],
        UserData=user_data
    )
    ec2_instance_id = ec2_instance['Instances'][0]['InstanceId']
    print(f"EC2 Instance created with ID: {ec2_instance_id}")

    ec2_waiter = ec2_client.get_waiter('instance_running')
    ec2_waiter.wait(InstanceIds=[ec2_instance_id])
    print(f"EC2 instance {ec2_instance_id} is running.")

    ec2_info = ec2_client.describe_instances(InstanceIds=[ec2_instance_id])
    public_ip = ec2_info['Reservations'][0]['Instances'][0]['PublicIpAddress']
    print(f"EC2 public IP: {public_ip}")

    print("\nSetup complete. You can access the web application at:")
    print(f"http://{public_ip}")
    print("\nNote: It may take a few minutes for the application to be fully operational.")
except ClientError as e:
    print(f"Error launching EC2 instance: {e}")
    raise