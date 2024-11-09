import os
from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector
from mysql.connector import Error

application = Flask(__name__)
app = application
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))

# MySQL Configuration from environment variables
db_config = {
    'host': os.environ.get('RDS_HOSTNAME', 'feedback-db.cniuq0gcmxho.ap-south-1.rds.amazonaws.com'),
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
    application.debug = True
    application.run()
