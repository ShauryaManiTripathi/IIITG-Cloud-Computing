import boto3
import time
import base64

# Initialize clients
ec2 = boto3.client('ec2')
autoscaling = boto3.client('autoscaling')
cloudwatch = boto3.client('cloudwatch')

# Define constants
AMI_ID = 'ami-02b49a24cfb95941c' 
INSTANCE_TYPE = 't2.micro'
KEY_NAME = 'test1'  
SECURITY_GROUP_NAME = 'WebServerSG'

def create_security_group():
    try:
        response = ec2.create_security_group(
            GroupName=SECURITY_GROUP_NAME,
            Description='Security group for web server with port 80 open'
        )
        security_group_id = response['GroupId']
        
        ec2.authorize_security_group_ingress(
            GroupId=security_group_id,
            IpPermissions=[
                {
                    'IpProtocol': 'tcp',
                    'FromPort': 80,
                    'ToPort': 80,
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
        print(f"Created Security Group: {security_group_id}")
        return security_group_id
    except ec2.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'InvalidGroup.Duplicate':
            response = ec2.describe_security_groups(GroupNames=[SECURITY_GROUP_NAME])
            return response['SecurityGroups'][0]['GroupId']
        else:
            raise

def create_launch_template(security_group_id):
    user_data = """#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello from AWS EC2 Auto Scaling!,"\u0053\u0068\u0061\u0075\u0072\u0079\u0061\u0020\u004D\u0061\u006E\u0069\u0020\u0054\u0072\u0069\u0070\u0061\u0074\u0068\u0069"</h1>" > /var/www/html/index.html
"""
    
    encoded_user_data = base64.b64encode(user_data.encode('utf-8')).decode('utf-8')
    
    try:
        response = ec2.create_launch_template(
            LaunchTemplateName='WebServerTemplate',
            VersionDescription='Web Server Template',
            LaunchTemplateData={
                'ImageId': AMI_ID,
                'InstanceType': INSTANCE_TYPE,
                'KeyName': KEY_NAME,
                'UserData': encoded_user_data,
                'SecurityGroupIds': [security_group_id],
            }
        )
        return response['LaunchTemplate']['LaunchTemplateId']
    except ec2.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'InvalidLaunchTemplateName.AlreadyExistsException':
            print("Launch template already exists. Using existing template.")
            response = ec2.describe_launch_templates(LaunchTemplateNames=['WebServerTemplate'])
            return response['LaunchTemplates'][0]['LaunchTemplateId']
        else:
            raise
def get_available_azs():
    response = ec2.describe_availability_zones(Filters=[{'Name': 'opt-in-status', 'Values': ['opt-in-not-required']}])
    return [az['ZoneName'] for az in response['AvailabilityZones']]


def create_auto_scaling_group(launch_template_id):
    try:
        autoscaling.create_auto_scaling_group(
            AutoScalingGroupName='WebServerASG',
            LaunchTemplate={
                'LaunchTemplateId': launch_template_id,
                'Version': '$Latest'
            },
            MinSize=1,
            MaxSize=3,
            DesiredCapacity=1,
            AvailabilityZones=get_available_azs(),  
        )
        print("Created Auto Scaling Group: WebServerASG")
    except autoscaling.exceptions.ClientError as e:
        if e.response['Error']['Code'] == 'AlreadyExists':
            print("Auto Scaling Group already exists. Skipping creation.")
        else:
            raise

def create_scaling_policies():
    try:
        scale_up_policy = autoscaling.put_scaling_policy(
            AutoScalingGroupName='WebServerASG',
            PolicyName='ScaleUpPolicy',
            PolicyType='SimpleScaling',
            AdjustmentType='ChangeInCapacity',
            ScalingAdjustment=1,
            Cooldown=300
        )
        
        scale_down_policy = autoscaling.put_scaling_policy(
            AutoScalingGroupName='WebServerASG',
            PolicyName='ScaleDownPolicy',
            PolicyType='SimpleScaling',
            AdjustmentType='ChangeInCapacity',
            ScalingAdjustment=-1,
            Cooldown=300
        )
        
        return scale_up_policy['PolicyARN'], scale_down_policy['PolicyARN']
    except autoscaling.exceptions.ClientError as e:
        print(f"Error creating scaling policies: {e}")
        return None, None

def create_cloudwatch_alarms(scale_up_policy_arn, scale_down_policy_arn):
    try:
        cloudwatch.put_metric_alarm(
            AlarmName='HighCPUUtilization',
            ComparisonOperator='GreaterThanThreshold',
            EvaluationPeriods=2,
            MetricName='CPUUtilization',
            Namespace='AWS/EC2',
            Period=30,
            Statistic='Average',
            Threshold=10.0,
            ActionsEnabled=True,
            AlarmActions=[scale_up_policy_arn],
            AlarmDescription='Alarm when CPU exceeds 10%',
            Dimensions=[
                {
                    'Name': 'AutoScalingGroupName',
                    'Value': 'WebServerASG'
                },
            ],
            Unit='Percent'
        )
        
        cloudwatch.put_metric_alarm(
            AlarmName='LowCPUUtilization',
            ComparisonOperator='LessThanThreshold',
            EvaluationPeriods=2,
            MetricName='CPUUtilization',
            Namespace='AWS/EC2',
            Period=30,
            Statistic='Average',
            Threshold=10.0,
            ActionsEnabled=True,
            AlarmActions=[scale_down_policy_arn],
            AlarmDescription='Alarm when CPU is less than 10%',
            Dimensions=[
                {
                    'Name': 'AutoScalingGroupName',
                    'Value': 'WebServerASG'
                },
            ],
            Unit='Percent'
        )
        print("Created CloudWatch Alarms")
    except cloudwatch.exceptions.ClientError as e:
        print(f"Error creating CloudWatch alarms: {e}")

def main():
    try:
        security_group_id = create_security_group()
        launch_template_id = create_launch_template(security_group_id)
        create_auto_scaling_group(launch_template_id)
        scale_up_policy_arn, scale_down_policy_arn = create_scaling_policies()
        if scale_up_policy_arn and scale_down_policy_arn:
            create_cloudwatch_alarms(scale_up_policy_arn, scale_down_policy_arn)
        
        print("Auto Scaling configuration complete. Waiting for instances to launch...")
        time.sleep(60)  
        
        response = autoscaling.describe_auto_scaling_groups(AutoScalingGroupNames=['WebServerASG'])
        instance_ids = [instance['InstanceId'] for instance in response['AutoScalingGroups'][0]['Instances']]
        
        if instance_ids:
            instance_response = ec2.describe_instances(InstanceIds=instance_ids)
            for reservation in instance_response['Reservations']:
                for instance in reservation['Instances']:
                    public_dns = instance.get('PublicDnsName')
                    if public_dns:
                        print(f"You can access the website at: http://{public_dns}")
        else:
            print("No instances have been launched yet. Please check the Auto Scaling group in the AWS console.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
