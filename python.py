import os
import time
import requests
import pymysql
from flask import Flask, request, render_template

app = Flask(__name__)

# Environment Variables for Database
DB_HOST = os.environ.get("DB_HOST", "localhost").split(":")[0]
DB_NAME = os.environ.get("DB_NAME", "testdb")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASS = os.environ.get("DB_PASS", "password")

def get_aws_metadata():
    """Dynamic IMDSv2 Metadata fetch for EC2/ASG/ALB labs"""
    try:
        token_url = "http://169.254.169.254/latest/api/token"
        headers = {"X-aws-ec2-metadata-token-ttl-seconds": "60"}
        token_res = requests.put(token_url, headers=headers, timeout=1)
        
        if token_res.status_code == 200:
            token = token_res.text
            meta_headers = {"X-aws-ec2-metadata-token": token}
            
            id_url = "http://169.254.169.254/latest/meta-data/instance-id"
            az_url = "http://169.254.169.254/latest/meta-data/placement/availability-zone"
            
            instance_id = requests.get(id_url, headers=meta_headers, timeout=1).text
            az = requests.get(az_url, headers=meta_headers, timeout=1).text
            return instance_id, az
    except Exception:
        pass
    return os.environ.get("INSTANCE_ID", "Local-Dev-PC"), os.environ.get("AZ", "local-zone")

@app.route("/", methods=["GET", "POST"])
def index():
    msg = ""
    db_error = None
    instance_id, az = get_aws_metadata()

    # Database connection & setup
    try:
        conn = pymysql.connect(
            host=DB_HOST, user=DB_USER, password=DB_PASS, database=DB_NAME,
            connect_timeout=3, cursorclass=pymysql.cursors.DictCursor
        )
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(100),
                    email VARCHAR(100)
                )
            """)
            conn.commit()

            if request.method == "POST":
                name = request.form.get("name")
                email = request.form.get("email")
                cursor.execute("INSERT INTO users (name, email) VALUES (%s, %s)", (name, email))
                conn.commit()
                msg = "✓ Data submitted to RDS successfully!"
        conn.close()
    except Exception as e:
        db_error = str(e)

    # Sending data cleanly to templates/index.html
    return render_template(
        "index.html", instance_id=instance_id, az=az, 
        msg=msg, db_error=db_error, db_host=DB_HOST
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
