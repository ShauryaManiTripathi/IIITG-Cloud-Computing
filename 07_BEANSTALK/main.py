import boto3
import os
import time
import shutil
import subprocess
from botocore.exceptions import ClientError
import json

class ElasticBeanstalkDeployer:
    def __init__(self, region='ap-south-1'):
        self.region = region
        self.eb_client = boto3.client('elasticbeanstalk', region_name=region)
        self.rds_client = boto3.client('rds', region_name=region)
        self.iam_client = boto3.client('iam', region_name=region)
        
        # Configuration
        self.application_name = 'feedback-app2'
        self.environment_name = 'feedback-env2'
        self.db_instance_identifier = 'feedback-db'
        self.instance_profile_name = 'aws-elasticbeanstalk-ec2-role'
        self.service_role_name = 'aws-elasticbeanstalk-service-role'
        self.solution_stack_name = '64bit Amazon Linux 2023 v4.2.0 running Python 3.12'

    def create_service_role(self):
        """Create the Elastic Beanstalk service role"""
        try:
            service_role_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "elasticbeanstalk.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }

            print("Creating Elastic Beanstalk service role...")
            self.iam_client.create_role(
                RoleName=self.service_role_name,
                AssumeRolePolicyDocument=json.dumps(service_role_policy)
            )

            # Attach necessary managed policies
            self.iam_client.attach_role_policy(
                RoleName=self.service_role_name,
                PolicyArn='arn:aws:iam::aws:policy/service-role/AWSElasticBeanstalkService'
            )

            # Wait for role to be available
            time.sleep(10)
            return self.iam_client.get_role(RoleName=self.service_role_name)['Role']['Arn']

        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                print(f"Service role {self.service_role_name} already exists.")
                return self.iam_client.get_role(RoleName=self.service_role_name)['Role']['Arn']
            else:
                raise

    def create_instance_profile(self):
        """Create the EC2 instance profile for Elastic Beanstalk"""
        try:
            instance_role_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "ec2.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            }

            print("Creating EC2 instance role...")
            self.iam_client.create_role(
                RoleName=self.instance_profile_name,
                AssumeRolePolicyDocument=json.dumps(instance_role_policy)
            )

            # Attach necessary managed policies
            managed_policies = [
                'arn:aws:iam::aws:policy/AWSElasticBeanstalkWebTier',
                'arn:aws:iam::aws:policy/AWSElasticBeanstalkMulticontainerDocker',
                'arn:aws:iam::aws:policy/AWSElasticBeanstalkWorkerTier'
            ]

            for policy in managed_policies:
                self.iam_client.attach_role_policy(
                    RoleName=self.instance_profile_name,
                    PolicyArn=policy
                )

            # Create instance profile
            print("Creating instance profile...")
            self.iam_client.create_instance_profile(
                InstanceProfileName=self.instance_profile_name
            )

            # Add role to instance profile
            self.iam_client.add_role_to_instance_profile(
                InstanceProfileName=self.instance_profile_name,
                RoleName=self.instance_profile_name
            )

            # Wait for instance profile to be available
            time.sleep(10)
            return self.instance_profile_name

        except ClientError as e:
            if e.response['Error']['Code'] == 'EntityAlreadyExists':
                print(f"Instance profile {self.instance_profile_name} already exists.")
                return self.instance_profile_name
            else:
                raise

    def create_application_files(self):
        """Create necessary application files and directories"""
        # Create base directory
        os.makedirs('feedback-app', exist_ok=True)
        os.chdir('feedback-app')
        
        # Create required directories
        directories = ['.ebextensions', 'templates', 'static']
        for directory in directories:
            os.makedirs(directory, exist_ok=True)

        # Create application.py
        with open('application.py', 'w') as f:
            f.write('''import os
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

application = Flask(__name__)
app = application
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# MySQL Configuration from environment variables
db_config = {
    'host': os.environ.get('RDS_HOSTNAME', 'localhost'),
    'user': os.environ.get('RDS_USERNAME', 'admin'),
    'password': os.environ.get('RDS_PASSWORD', 'password'),
    'database': os.environ.get('RDS_DB_NAME', 'feedback'),
    'port': int(os.environ.get('RDS_PORT', 3306))
}

def create_connection():
    try:
        connection = mysql.connector.connect(**db_config)
        return connection
    except Error as e:
        print(f"Error connecting to MySQL: {e}")
        return None

def create_table():
    try:
        connection = create_connection()
        cursor = connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INT AUTO_INCREMENT PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                email VARCHAR(100) NOT NULL,
                message TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        connection.commit()
    except Error as e:
        print(f"Error creating table: {e}")
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/submit_feedback', methods=['POST'])
def submit_feedback():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        message = request.form['message']

        try:
            connection = create_connection()
            cursor = connection.cursor()
            query = "INSERT INTO feedback (name, email, message) VALUES (%s, %s, %s)"
            values = (name, email, message)
            cursor.execute(query, values)
            connection.commit()
            flash('Feedback submitted successfully!', 'success')
        except Error as e:
            print(f"Error inserting feedback: {e}")
            flash('An error occurred. Please try again.', 'error')
        finally:
            if connection and connection.is_connected():
                cursor.close()
                connection.close()

    return redirect(url_for('index'))

@app.route('/all_feedbacks')
def all_feedbacks():
    try:
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT * FROM feedback ORDER BY created_at DESC")
        feedbacks = cursor.fetchall()
        return render_template('all_feedbacks.html', feedbacks=feedbacks)
    except Error as e:
        print(f"Error fetching feedbacks: {e}")
        flash('An error occurred while fetching feedbacks.', 'error')
        return redirect(url_for('index'))
    finally:
        if connection and connection.is_connected():
            cursor.close()
            connection.close()

if __name__ == '__main__':
    create_table()
    application.run(host='0.0.0.0', port=8080)
''')

        # Create requirements.txt
        with open('requirements.txt', 'w') as f:
            f.write('''Flask==2.0.1
mysql-connector-python==8.0.26
Werkzeug==2.0.1
''')

        # Create .ebextensions configuration
        with open('.ebextensions/01_flask.config', 'w') as f:
            f.write('''option_settings:
  aws:elasticbeanstalk:container:python:
    WSGIPath: application:application
  aws:elasticbeanstalk:environment:proxy:staticfiles:
    /static: static
''')

        # Create Procfile
        with open('Procfile', 'w') as f:
            f.write('web: python application.py')

        # Create templates
        self._create_templates()

    def _create_templates(self):
        """Create HTML templates"""
        # Create index.html
        with open('templates/index.html', 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Feedback Form</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f0f4f8;
        }
        form {
            background-color: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        input, textarea {
            width: 100%;
            padding: 8px;
            margin: 8px 0;
            border: 1px solid #ddd;
            border-radius: 4px;
        }
        button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 15px;
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }
    </style>
</head>
<body>
    <h1>Feedback Form</h1>
    {% with messages = get_flashed_messages(with_categories=true) %}
        {% if messages %}
            {% for category, message in messages %}
                <div class="flash-{{ category }}">{{ message }}</div>
            {% endfor %}
        {% endif %}
    {% endwith %}
    <form action="{{ url_for('submit_feedback') }}" method="POST">
        <input type="text" name="name" placeholder="Your Name" required>
        <input type="email" name="email" placeholder="Your Email" required>
        <textarea name="message" placeholder="Your Feedback" rows="5" required></textarea>
        <button type="submit">Submit Feedback</button>
    </form>
    <a href="{{ url_for('all_feedbacks') }}">View All Feedbacks</a>
</body>
</html>''')

        # Create all_feedbacks.html
        with open('templates/all_feedbacks.html', 'w') as f:
            f.write('''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>All Feedbacks</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f0f4f8;
        }
        table {
            width: 100%;
            border-collapse: collapse;
            background-color: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        th, td {
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }
        th {
            background-color: #4CAF50;
            color: white;
        }
    </style>
</head>
<body>
    <h1>All Feedbacks</h1>
    <table>
        <thead>
            <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Message</th>
                <th>Created At</th>
            </tr>
        </thead>
        <tbody>
            {% for feedback in feedbacks %}
            <tr>
                <td>{{ feedback.name }}</td>
                <td>{{ feedback.email }}</td>
                <td>{{ feedback.message }}</td>
                <td>{{ feedback.created_at }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>
    <a href="{{ url_for('index') }}">Back to Feedback Form</a>
</body>
</html>''')

    def create_rds_instance(self):
        """Create RDS instance"""
        try:
            print("Creating RDS instance...")
            response = self.rds_client.create_db_instance(
                DBInstanceIdentifier=self.db_instance_identifier,
                AllocatedStorage=20,
                DBInstanceClass='db.t4g.micro',
                Engine='mysql',
                MasterUsername='admin',
                MasterUserPassword='password',  # Change this in production
                DBName='feedback',
                PubliclyAccessible=True,
                BackupRetentionPeriod=7
            )
            
            # Wait for the RDS instance to be available
            print("Waiting for RDS instance to be available...")
            waiter = self.rds_client.get_waiter('db_instance_available')
            waiter.wait(DBInstanceIdentifier=self.db_instance_identifier)
            
            # Get the RDS endpoint
            rds_info = self.rds_client.describe_db_instances(
                DBInstanceIdentifier=self.db_instance_identifier
            )
            return rds_info['DBInstances'][0]['Endpoint']['Address']
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'DBInstanceAlreadyExists':
                print(f"RDS instance {self.db_instance_identifier} already exists.")
                rds_info = self.rds_client.describe_db_instances(
                    DBInstanceIdentifier=self.db_instance_identifier
                )
                return rds_info['DBInstances'][0]['Endpoint']['Address']
            else:
                raise

    def deploy_to_elastic_beanstalk(self, rds_endpoint):
        """Deploy application to Elastic Beanstalk"""
        try:
            # Create necessary IAM roles first
            service_role_arn = self.create_service_role()
            instance_profile = self.create_instance_profile()

            # Create Elastic Beanstalk application
            print("Creating Elastic Beanstalk application...")
            self.eb_client.create_application(
                ApplicationName=self.application_name,
                Description='Feedback Application'
            )
        except ClientError as e:
            if e.response['Error']['Code'] == 'ApplicationAlreadyExists':
                print(f"Application {self.application_name} already exists.")
            else:
                raise

        try:
            # Create Elastic Beanstalk environment
            print("Creating Elastic Beanstalk environment...")
            response = self.eb_client.create_environment(
                ApplicationName=self.application_name,
                EnvironmentName=self.environment_name,
                SolutionStackName=self.solution_stack_name,
                OptionSettings=[
                    {
                        'Namespace': 'aws:autoscaling:launchconfiguration',
                        'OptionName': 'IamInstanceProfile',
                        'Value': instance_profile
                    },
                    {
                        'Namespace': 'aws:elasticbeanstalk:environment',
                        'OptionName': 'ServiceRole',
                        'Value': service_role_arn
                    },
                    {
                        'Namespace': 'aws:autoscaling:launchconfiguration',
                        'OptionName': 'InstanceType',
                        'Value': 't2.micro'
                    },
                    {
                        'Namespace': 'aws:elasticbeanstalk:application:environment',
                        'OptionName': 'RDS_HOSTNAME',
                        'Value': rds_endpoint
                    },
                    {
                        'Namespace': 'aws:elasticbeanstalk:application:environment',
                        'OptionName': 'RDS_PORT',
                        'Value': '3306'
                    },
                    {
                        'Namespace': 'aws:elasticbeanstalk:application:environment',
                        'OptionName': 'RDS_DB_NAME',
                        'Value': 'feedback'
                    },
                    {
                        'Namespace': 'aws:elasticbeanstalk:application:environment',
                        'OptionName': 'RDS_USERNAME',
                        'Value': 'admin'
                    },
                    {
                        'Namespace': 'aws:elasticbeanstalk:application:environment',
                        'OptionName': 'RDS_PASSWORD',
                        'Value': 'password'  # Change this in production
                    }
                ]
            )
            
            # Wait for environment to be ready using describe_environments instead of waiter
            print("Waiting for environment to be ready...")
            while True:
                env_response = self.eb_client.describe_environments(
                    ApplicationName=self.application_name,
                    EnvironmentNames=[self.environment_name]
                )
                
                if not env_response['Environments']:
                    print("Environment not found. Waiting...")
                    time.sleep(10)
                    continue
                
                status = env_response['Environments'][0]['Status']
                health = env_response['Environments'][0]['Health']
                
                print(f"Environment status: {status}, health: {health}")
                
                if status == 'Ready' and health in ['Green', 'Yellow']:
                    break
                elif status in ['Terminated', 'Terminating']:
                    raise Exception(f"Environment failed to deploy. Status: {status}")
                
                time.sleep(10)
            
            return response['EndpointURL']
            
        except ClientError as e:
            print(f"Error creating environment: {e}")
            raise

def main():
    deployer = ElasticBeanstalkDeployer()
    
    # Create application files
    print("Creating application files...")
    deployer.create_application_files()
    
    # Create RDS instance
    print("Setting up RDS...")
    rds_endpoint = deployer.create_rds_instance()
    print(f"RDS endpoint: {rds_endpoint}")
    
    # Deploy to Elastic Beanstalk
    print("Deploying to Elastic Beanstalk...")
    endpoint_url = deployer.deploy_to_elastic_beanstalk(rds_endpoint)
    
    print("\nDeployment completed!")
    print(f"Your application is available at: http://{endpoint_url}")
    print("\nNote: It may take a few minutes for the application to be fully operational.")

if __name__ == "__main__":
    main()