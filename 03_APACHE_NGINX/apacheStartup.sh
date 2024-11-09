#!/bin/bash
apt update -y
apt install -y apache2
systemctl start apache2
systemctl enable apache2

sudo snap install aws-cli --classic

sudo aws configure set aws_access_key_id {a}
sudo aws configure set aws_secret_access_key {b}
sudo aws configure set default.region ap-south-1
sudo aws configure set default.output json

sudo aws s3 cp s3://shauryatripathi22b/Website/ /var/www/html/ --recursive

sudo aws s3 cp s3://shauryatripathi22b/Website/ /var/www/html/ --recursive > /tmp/s3_copy_log.txt 2>&1

chown -R www-data:www-data /var/www/html
chmod -R 755 /var/www/html