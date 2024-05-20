import os
import requests
import jinja2
import datetime
from dotenv import load_dotenv

# tasks.py a different process from app.py. That's why you need to load env file
APP_ROOT = os.path.join(os.path.dirname(__file__))
FLASK_ENV = os.getenv("FLASK_ENV") or "development"

ENVIRONMENTS = {"development": ".env", "qa": "qa.env.", "production": "prod.env"}

dotenv_path = os.path.join(APP_ROOT, ENVIRONMENTS.get(FLASK_ENV) or ".env")
load_dotenv(dotenv_path)

mailgun_api_key = os.getenv("MAILGUN_API_KEY")
mailgun_domain = os.getenv("MAILGUN_DOMAIN")

template_loader = jinja2.FileSystemLoader("templates")
template_env = jinja2.Environment(loader=template_loader)


def render_template(template_filename, **context):
    return template_env.get_template(template_filename).render(**context)


def send_simple_message(to, subject, body, html):
    time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return requests.post(
        f"https://api.mailgun.net/v3/{mailgun_domain}/messages",
        auth=("api", mailgun_api_key),
        data={
            "from": f"Exuberant User <mailgun@{mailgun_domain}>",
            "to": [to],
            "subject": time + subject,
            "text": body,
            "html": html,
        },
    )


def send_user_registration_email(email, username):
    return send_simple_message(
        email,
        "Successfully signed up",
        f"Hi {username}! You've successfully registered.",
        render_template("email/action.html", username=username),
    )
