import boto3

ec2_client = boto3.client('ec2', region_name='ap-south-1')
rds_client = boto3.client('rds', region_name='ap-south-1')

# Define EC2 and RDS configurations
ec2_instance_type = 't2.micro' 
ami_id = 'ami-0dee22c13ea7a9a67'
key_name = 'test1'  
security_group_name = 'default' 
db_instance_identifier = 'feedback-db'
db_instance_class = 'db.t4g.micro' 
db_engine = 'mysql'
db_name = 'feedback'
db_master_username = 'admin'
db_master_password = 'password'

# Create security group
response = ec2_client.create_security_group(
    GroupName=security_group_name,
    Description='Security group for EC2 and RDS communication'
)

security_group_id = response['GroupId']

# Launch EC2 instance with user-data for setup
with open('userdata.txt', 'r') as userdata_file:
    user_data = userdata_file.read()

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

# Create RDS instance
rds_instance = rds_client.create_db_instance(
    DBInstanceIdentifier=db_instance_identifier,
    AllocatedStorage=20,  # Minimum storage for RDS (in GB)
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

waiter = rds_client.get_waiter('db_instance_available')
waiter.wait(DBInstanceIdentifier=db_instance_identifier)
print(f"RDS instance {db_instance_identifier} is available.")
