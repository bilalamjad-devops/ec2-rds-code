import os
import requests
import pymysql
from flask import Flask, request, render_template_string

app = Flask(__name__)

# 1. Database Configurations via standard Environment Variables
DB_HOST = os.environ.get("DB_HOST", "localhost").split(":")[0]
DB_NAME = os.environ.get("DB_NAME", "testdb")
DB_USER = os.environ.get("DB_USER", "root")
DB_PASS = os.environ.get("DB_PASS", "password")

def get_aws_metadata():
    """Queries IMDSv2 dynamically. Falls back cleanly if run locally."""
    try:
        # Step A: Request the security session token (Valid for 60 seconds)
        token_url = "http://169.254.169.254/latest/api/token"
        headers = {"X-aws-ec2-metadata-token-ttl-seconds": "60"}
        token_res = requests.put(token_url, headers=headers, timeout=1)
        
        if token_res.status_code == 200:
            token = token_res.text
            meta_headers = {"X-aws-ec2-metadata-token": token}
            
            # Step B: Grab Instance ID and AZ
            id_url = "http://169.254.169.254/latest/meta-data/instance-id"
            az_url = "http://169.254.169.254/latest/meta-data/placement/availability-zone"
            
            instance_id = requests.get(id_url, headers=meta_headers, timeout=1).text
            az = requests.get(az_url, headers=meta_headers, timeout=1).text
            return instance_id, az
    except Exception:
        pass
    # Fallback strings for local laptop test / Docker test
    return os.environ.get("INSTANCE_ID", "Local-Development-Box"), os.environ.get("AZ", "localhost-zone")

# 2. Minimalist HTML structure based directly on your template
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>AWS 3-Tier Demo</title>
    <style>
        body { font-family: Arial, sans-serif; background: #f4f6f9; padding: 30px; }
        .box { max-width: 600px; margin: auto; background: white; padding: 25px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .highlight { color: #ff9900; font-weight: bold; }
        input[type=text], input[type=email] { width: 100%; padding: 10px; margin: 10px 0; box-sizing: border-box; }
        input[type=submit] { background: #ff9900; border: none; padding: 10px 20px; color: white; cursor: pointer; }
    </style>
</head>
<body>
<div class="box">
    <h2>AWS 3-Tier Enterprise Lab</h2>
    <p>Served From Instance ID: <span class="highlight">{{ instance_id }}</span></p>
    <p>Availability Zone: <span class="highlight">{{ az }}</span></p>
    <hr>
    <h3>Submit Info to RDS</h3>
    
    {% if db_error %}
        <p style="color: red;"><b>⚠️ DB Alert: {{ db_error }}</b></p>
    {% else %}
        <p style="color: #ff9900;"><b>✓ Connected to MySQL Database ({{ db_host }})</b></p>
    {% endif %}

    <form method="POST">
        Name: <input type="text" name="name" required><br>
        Email: <input type="email" name="email" required><br>
        <input type="submit" value="Submit Data">
    </form>
    
    {% if msg %}
        <p style="color: green;"><b>{{ msg }}</b></p>
    {% endif %}
</div>
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    msg = ""
    db_error = None
    instance_id, az = get_aws_metadata()

    # Database Initialization & Operations
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

    return render_template_string(
        HTML_TEMPLATE, instance_id=instance_id, az=az, 
        msg=msg, db_error=db_error, db_host=DB_HOST
    )

if __name__ == "__main__":
    # Runs on port 8080 by default for easy testing
    app.run(host="0.0.0.0", port=8080)
