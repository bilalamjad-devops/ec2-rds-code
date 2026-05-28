# ec2-rds-code



```code
pip install flask requests pymysql
```

```py
python app.py
```



## 💻 Step 1: The App Code (`app.py`)

Create a folder on your computer and save this file as `app.py`.

This code has a built-in safety net: if it runs on AWS, it grabs real instance attributes. If it runs locally on your computer or inside Docker, it catches the timeout and falls back to displaying `"Local Machine"` or custom variables so it never crashes!

```python
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

```

---

## 🏃‍♂️ Step 2: Running it Locally (Manual Test)

To verify everything works before touching Docker or AWS, test it right on your local terminal:

1. Install the required dependencies:
```bash
pip install flask requests pymysql

```


2. Run the application:
```bash
python app.py

```


3. Open `http://localhost:8080` in your browser.

> You will see your exact UI panel layout! It will show a database error because no local MySQL instance is running yet, which confirms the verification path is working cleanly.

---

## 🐳 Step 3: Package it into a Docker Image

To run this application as an isolated container anywhere (or inside AWS ECS/EKS later down the road), create a file named **`Dockerfile`** in the same folder:

```dockerfile
# Use a lightweight python base image
FROM python:3.11-slim

# Create and switch to working app directory
WORKDIR /app

# Install system dependencies needed for network requests
RUN pip install --no-cache-dir flask requests pymysql

# Copy our app file into the container
COPY app.py .

# Expose Web Port 8080
EXPOSE 8080

# Execute the application
CMD ["python", "app.py"]

```

### Build and Run Your Docker Container:

```bash
# 1. Build the image
docker build -t aws-3tier-app:v1 .

# 2. Spin up the container on port 8080
docker run -p 8080:8080 aws-3tier-app:v1

```

Go back to your browser at `http://localhost:8080`—now your containerized deployment is running exactly the same way.

---

## ☁️ Step 4: Using This App on AWS (EC2 UserData)

When you are ready to take this application to an EC2 instance (or inside an Auto Scaling Group behind an ALB), you don't even need to mess with Docker registries yet if you don't want to. You can just write a clean **`userdata.sh`** that pulls down Python, pulls this code file, and boots it up.

Here is the script to deploy it automatically via your infrastructure automation:

```bash
#!/bin/bash
set -e

# 1. Update OS packages and set up Python
dnf update -y
dnf install -y python3 python3-pip

# 2. Install application packages
pip3 install flask requests pymysql

# 3. Export your live Terraform database values to the environment scope
export DB_HOST="${db_host}"
export DB_NAME="${db_name}"
export DB_USER="${db_user}"
export DB_PASS="${db_password}"

# 4. Write the application code file directly to disk
cat > /var/local/app.py << 'EOF'
${python_content}
EOF

# 5. Launch app on standard HTTP port 80 in background mode
# Change 'port=8080' to 'port=80' at runtime execution
sed -i 's/port=8080/port=80/g' /var/local/app.py
nohup python3 /var/local/app.py > /var/log/app_engine.log 2>&1 &

```

### Why this fits perfectly for ASG + ALB:

When an Auto Scaling Group launches 3 different instances from this configuration, **each instance** will fetch its own unique identity via the `get_aws_metadata()` function.

As you refresh the Application Load Balancer IP address, you will watch the **Instance ID** text instantly switch back and forth on your screen, proving your multi-tier load-balancing architecture is operating exactly as designed.
