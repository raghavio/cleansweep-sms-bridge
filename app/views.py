from app import app
from flask import request, jsonify
import shlex
import requests


@app.route("/")
def index():
    return "Hello, World!"


@app.route("/sms-bridge/", methods=['GET'])
def handle_request():
    if 'password' not in request.args or not request.args.get('password') or \
            'phone' not in request.args or not request.args.get('phone') or \
            'message' not in request.args or not request.args.get('message'):
        return jsonify(), 400

    password = request.args.get('password')
    if password != app.config['PASSWORD']:
        return jsonify(), 401

    phone = request.args.get('phone')

    sms_text = request.args.get('message')
    sms_text_parts = shlex.split(sms_text)  # Splits by whitespace but text in quotes stays intact.

    task = sms_text_parts[0].lower()

    response = _authorize(task, phone)
    data = response.json()

    is_authorized = response.status_code == "200"
    if is_authorized:
        token = data['token']  # Grab token if authorized
        if task == "sendsms":
            response = _send_sms(token, sms_text_parts)
        else:
            response = None
    else:
        return jsonify({'feedback': data['error']}), data.status_code

    data = response.json()
    is_successful = response.status_code == 200
    return jsonify({"feedback": data['feedback'] if is_successful else data['error']}), response.status_code


def _authorize(task, phone):
    """
    Authorize the app by sending client-id and client-secret.
    This also checks if user (phone) has permission for the specified task.

    :param task: The task to perform
    :param phone: User's phone number.
    :return: Response from the server in a request object.
    This is what the server is going to return:

    If authorized
    200 OK

    {
        "scope": <scope>,
        "phone": <phone>,
        "token": <token>
    }

    If no user can be found from that phone number
    404 Not Found

    {
        "error": "No such user found"
    }

    If user does not have permission
    403 Forbidden

    {
        "error": "The user does not have permission"
    }
    """
    data = {
        'client-id': app.config['CLIENT_ID'],
        'client-secret': app.config['CLIENT_SECRET'],
        'scope': task,
        'phone': phone
    }
    response = requests.post('http://cleansweep.herokuapp.com/api/authorize', data)
    return response


def _send_sms(token, sms_text_parts):
    """
    Sends a request to send group sms to all the volunteers of a place.
    :param token: The token to communicate with server
    :param sms_text_parts: The exact sms user sent, split by whitespace.
                            Contains place and the message to send.
    :return: Response from the server in a request object.
    This is what the server is going to return:

    If successfully sent
    200 OK

    {
        "message": "Message delivered",
        "count": "34"
    }

    If token did not match
    403 Forbidden

    {
        "error": "Token did not match."
    }
    """
    if len(sms_text_parts) != 3:  # If sending sms, there can be only 3 parts. 1st task, 2nd place and 3rd the message.
        return None
    data = {
        'token': token,
        'client-id': app.config['CLIENT_ID'],
        'place': sms_text_parts[1],
        'message': sms_text_parts[2]
    }
    return requests.post('http://localhost:5000/api/send-sms', data)
