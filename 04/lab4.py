import boto3
import time
import os

# Initialize EC2 client
ec2 = boto3.client('ec2')

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

def launch_instance(instance_type, ami_id, count=1,security_group_id=security_group_id):
    response = ec2.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        MinCount=count,
        MaxCount=count,
        SecurityGroupIds=[security_group_id],
    )
    return [instance['InstanceId'] for instance in response['Instances']]

def launch_instance_with_website(instance_type, ami_id, count=1,security_group_id=security_group_id):
    user_data = """#!/bin/bash
yum update -y
yum install -y httpd
systemctl start httpd
systemctl enable httpd
echo "<h1>Hello from AWS EC2!, This is shaurya Mani Tripathi</h1>" > /var/www/html/index.html
"""
    response = ec2.run_instances(
        ImageId=ami_id,
        InstanceType=instance_type,
        MinCount=count,
        MaxCount=count,
        SecurityGroupIds=[security_group_id],
        UserData=user_data
    )
    # print dns link
    instance = ec2.describe_instances(InstanceIds=[response['Instances'][0]['InstanceId']])['Reservations'][0]['Instances'][0]
    public_dns = instance['PublicDnsName']
    print(f"You can access the website at: http://{public_dns}")
    return [instance['InstanceId'] for instance in response['Instances']]




def list_instances():
    response = ec2.describe_instances(
        Filters=[{'Name': 'instance-state-name', 'Values': ['running']}]
    )
    instances = []
    for reservation in response['Reservations']:
        instances.extend(reservation['Instances'])
    return instances

def check_instance_health(instance_ids):
    response = ec2.describe_instance_status(InstanceIds=instance_ids)
    return response['InstanceStatuses']


def stop_instances(instance_ids):
    ec2.stop_instances(InstanceIds=instance_ids)
    print(f"Stopping instances: {instance_ids}")
    waiter=ec2.get_waiter('instance_stopped')
    waiter.wait(InstanceIds=instance_ids)

def terminate_instances(instance_ids):
    ec2.terminate_instances(InstanceIds=instance_ids)
    print(f"Terminating instances: {instance_ids}")
    waiter=ec2.get_waiter('instance_terminated')
    waiter.wait(InstanceIds=instance_ids)

def start_instances(instance_ids):
    ec2.start_instances(InstanceIds=instance_ids)
    print(f"Starting instances: {instance_ids}")
    waiter=ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=instance_ids)
    print(f"waiting for ok status: {instance_ids}")
    waiter2=ec2.get_waiter('instance_status_ok')
    waiter2.wait(InstanceIds=instance_ids)

def host_http_server(instance_id):
    user_data = """#!/bin/bash
sudo yum update -y
sudo yum install -y httpd
sudo systemctl start httpd
sudo systemctl enable httpd
sudo echo "<h1>Hello from AWS EC2!, This is shaurya Mani Tripathi</h1>" > /var/www/html/index.html
"""
    ec2.stop_instances(InstanceIds=[instance_id])
    print("Waiting for instance to stop...")
    waiter = ec2.get_waiter('instance_stopped')
    waiter.wait(InstanceIds=[instance_id])
    print("Instance stopped")
    print("modifying user data")
    ec2.modify_instance_attribute(
        InstanceId=instance_id,
        UserData={'Value': user_data}
    )
    time.sleep(10)
    ec2.start_instances(InstanceIds=[instance_id])
    print("Waiting for instance to start...")
    waiter = ec2.get_waiter('instance_running')
    waiter.wait(InstanceIds=[instance_id])
    print("Instance started")
    print("waiting for ok status")
    waiter2 = ec2.get_waiter('instance_status_ok')
    waiter2.wait(InstanceIds=[instance_id])
    print("Instance is healthy")
    # Print the public DNS name of the instance to access the website
    instance = ec2.describe_instances(InstanceIds=[instance_id])['Reservations'][0]['Instances'][0]
    public_dns = instance['PublicDnsName']
    print(f"You can access the website at: http://{public_dns}")

def main():
    # Launch t2.micro Amazon Linux instance
    amazon_linux_ami = 'ami-02b49a24cfb95941c'  # Amazon Linux 2023 AMI
    micro_instance = launch_instance_with_website('t2.micro', amazon_linux_ami)[0]
    print(f"Launched t2.micro instance: {micro_instance}")

    # Launch two t2.micro Ubuntu instances
    ubuntu_ami = 'ami-0522ab6e1ddcc7055'  # Ubuntu Server 24.04 LTS (HVM), SSD Volume Type
    micro_instances = launch_instance('t2.micro', ubuntu_ami, count=2)
    print(f"Launched two more t2.micro instances with ubuntu image: {micro_instances}")

    # Create a list of instance IDs to check
    instance_ids = [micro_instance] + micro_instances
    waiter = ec2.get_waiter('instance_running')
    print(f"Waiting for instances to be in running state: {instance_ids}")
    waiter.wait(InstanceIds=instance_ids)

    # List all running instances
    running_instances = list_instances()
    print("Running instances:")
    for instance in running_instances:
        print(f"ID: {instance['InstanceId']}, Type: {instance['InstanceType']}, State: {instance['State']['Name']}")

    # Check health of running instances
    all_instance_ids = [micro_instance] + micro_instances
    waiter2 = ec2.get_waiter('instance_status_ok')
    print(f"Waiting for instances to be in healthy state: {all_instance_ids}")
    waiter2.wait(InstanceIds=all_instance_ids)
    health_statuses = check_instance_health(all_instance_ids)


    print("Instance health:")
    for status in health_statuses:
        print(f"ID: {status['InstanceId']}, Status: {status['InstanceStatus']['Status']}")


    # # Host HTTP server on t2.micro instance
    # print("Hosting HTTP server on t2.micro instance")
    # host_http_server(micro_instance)
    # print(f"Hosted HTTP server on instance: {micro_instance}")

    input("Press any key to stop and terminate all instances: ")

    # Terminate instances
    terminate_instances(all_instance_ids)
    print("Terminated all instances")

if __name__ == "__main__":
    main()