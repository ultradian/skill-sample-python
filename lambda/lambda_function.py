"""lambda_function.py: lambda skill."""
from datetime import datetime, timedelta
from decimal import Decimal
from botocore.exceptions import ClientError
from constants import (
    PRINT_LIMIT,
    STATE, START_STATE,
    GO_INTENT,
    SPEECHOUTPUT, REPROMPT,
    VISIT_COUNT,
    DB_TABLE_NAME, USERID, DATA, TIMESTAMP,
    SHORT_PAUSE, VOCAB,
    LAUNCH_TIME, ENTRY_TIME, RESPONSE_TIME, EXIT_TIME,
    MAX_RESPONSE_TIME, MAX_SESSION_TIME
)
import os
if os.environ.get("AWS_EXECUTION_ENV") is not None:
    print(f"os.environ is {os.environ}")
    from services import DYNAMODB, DB_TABLE
else:
    from mock_services import DYNAMODB, DB_TABLE

__version__ = '0.0.1'
__author__ = 'Milton Huang'


# --------------- entry point -----------------
def lambda_handler(event, context):
    """App entry point."""
    userId = get_userId(event)
    attributes = get_attributes(event)
    now = datetime.utcnow().isoformat()
    attributes[ENTRY_TIME] = now
    print(f"DEBUG: in lambda_handler with {event} at {now}")
    put_dbdata(DB_TABLE, userId, attributes)
    request_type = event['request']['type']
    if request_type == 'LaunchRequest':
        return on_launch(event)
    elif request_type == 'IntentRequest':
        return on_intent(event)
    elif request_type == 'SessionEndedRequest':
        return on_session_ended(event)
    else:
        print("WARNING: Unhandled event in lambda_handler:", event)
        return confused_response(event)


# --------------- request handlers -----------------
def on_launch(event):
    """Start session."""
    init_attributes(event)
    print(f"DEBUG: in on_launch with {event}")
    return go_response(event)


def on_intent(event):
    """Process intent."""
    intent_name = event['request']['intent']['name']
    print(f"on_intent: {intent_name}")
    if ('session' in event and 'new' in event['session'] and
       event['session']['new'] and
       event['request']['type'] != 'LaunchRequest'):
        init_attributes(event)
    if intent_name in ('AMAZON.StopIntent', 'AMAZON.CancelIntent'):
        return stop_response(event)
    elif intent_name == 'AMAZON.HelpIntent':
        return help_response(event)
    elif intent_name == GO_INTENT:
        return go_response(event)
    else:
        print("WARNING: unhandled intent in on_intent", intent_name)
        return confused_response(event)


def stop_response(event):
    """Give stop message response."""
    userId = get_userId(event)
    attributes = get_attributes(event)
    messages = get_message(get_locale(event))
    put_dbdata(DB_TABLE, userId, attributes)
    response = tell_response(messages['STOP_MESSAGE'])
    return service_response(event, response)


def help_response(event):
    """Give help response."""
    messages = get_message(get_locale(event))
    speechmessage = messages['HELP_MESSAGE']
    reprompt = messages['HELP_MESSAGE']
    response = ask_response(speechmessage, reprompt)
    return service_response(event, response)


def confused_response(event):
    """Return FALLBACK_MESSAGE response."""
    messages = get_message(get_locale(event))
    speechmessage = messages['FALLBACK_MESSAGE']
    reprompt = messages['FALLBACK_REPROMPT']
    response = ask_response(speechmessage, reprompt)
    return service_response(event, response)


def go_response(event):
    """Return go response."""
    messages = get_message(get_locale(event))
    speechmessage = messages['GO_MESSAGE']
    reprompt = messages['GO_REPROMPT']
    response = ask_response(speechmessage, reprompt)
    return service_response(event, response)


def on_session_ended(event):
    """Cleanup session."""
    attributes = get_attributes(event)
    userId = get_userId(event)
    now = datetime.utcnow().isoformat()
    attributes[EXIT_TIME] = now
    put_dbdata(DB_TABLE, userId, attributes)
    print(f"Exit thru on_session_ended with {attributes} at {now}")
    print(f"total duration: {datetime.fromisoformat(now) - datetime.fromisoformat(attributes[LAUNCH_TIME])}") # noqa
    return {
        "version": "1.0",
        "response": {}
    }


# ------------------------------ request helpers -----------------
def get_message(locale):
    """Get message strings for `locale`."""
    return VOCAB[locale]['messages']


def get_locale(event):
    """Get locale from event."""
    request = event['request']
    if 'locale' in request:
        locale = request['locale']
    else:
        locale = 'en-US'
    return locale


def get_userId(event):
    """Get userId from event."""
    userId = event['context']['System']['user']['userId']
    print("userId: ", userId)
    return userId


def get_access_token(event):
    """Get api access token from request."""
    if 'apiAccessToken' in event['context']['System']:
        token = event['context']['System']['apiAccessToken']
        print("get_access_token: ", token)
        if token:
            return token
    print("ERROR: no token in get_access_token:", event)
    return ""


def init_attributes(event):
    """Initialize session['attributes']."""
    now = datetime.utcnow().isoformat()
    print(f"DEBUG: starting session with {event} at {now}")
    if 'session' not in event or 'attributes' not in event['session']:
        userId = get_userId(event)
        attributes = get_dbdata(DB_TABLE, userId)
        if attributes is None or VISIT_COUNT not in attributes:
            # first time
            attributes[VISIT_COUNT] = 0
            attributes[MAX_RESPONSE_TIME] = 0
            attributes[MAX_SESSION_TIME] = 0
    else:
        attributes = event['session']['attributes']
    attributes[LAUNCH_TIME] = now
    attributes[VISIT_COUNT] += 1
    attributes[STATE] = START_STATE
    event['session']['attributes'] = attributes


def get_attributes(event, attr=''):
    """Return session['attributes'] object."""
    if 'session' not in event or 'attributes' not in event['session']:
        userId = get_userId(event)
        attributes = get_dbdata(DB_TABLE, userId)
        if attributes is not None:
            return attributes
        return {}
    return event['session']['attributes']


# --------------- data helpers -----------------
def clean_data_strings(data):
    """Replace empty strings in data with ' '."""
    for key in data:
        if data[key] == '':
            data[key] = ' '
        if isinstance(data[key], float):
            data[key] = int(data[key])
        elif isinstance(data, dict):
            if isinstance(data[key], float):
                data[key] = int(data[key])
            if isinstance(data[key], (dict, list)):
                data[key] = clean_data_strings(data[key])
    return data


def restore_empty_strings(data):
    """Replace ' ' with empty strings in data."""
    for i, key in enumerate(data):
        if isinstance(data, list):
            if key == " ":
                data[i] = ""
            if isinstance(key, Decimal):
                data[i] = int(data[i])
            if isinstance(key, (dict, list)):
                data[i] = restore_empty_strings(data[i])
        elif isinstance(data, dict):
            if data[key] == ' ':
                data[key] = ''
            if isinstance(data[key], Decimal):
                data[key] = int(data[key])
            if isinstance(data[key], (dict, list)):
                data[key] = restore_empty_strings(data[key])
    return data


def get_dbdata(table, id):
    """
    Fetch data for user.

    Args:
    table -- dynamodb table
    id -- userId to fetch
    """
    # TODO: if Requested resource not found, handle it
    try:
        response = table.get_item(
            Key={
                USERID: id
            }
        )
        print("get response:", response)
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        print("WARNING: error in get_dbdata:", error_msg)
        if error_msg == "Requested resource not found":
            # no table
            print("WARNING: creatng new table in get_dbdata")
            table = make_dynamodb_table(DB_TABLE_NAME)
        item = {}
    else:
        if 'Item' not in response:
            print("Creating since No Item in get_dbdata:", response)
            put_dbdata(table, id, {})
            return {}
        if DATA in response['Item']:
            item = response['Item'][DATA]
            item = restore_empty_strings(item)
            print("GetItem succeeded: ", item)
        else:
            item = {}
    return item


def put_dbdata(table, id, data):
    """
    Save data for user.

    Args:
    table -- dynamodb table
    id -- userId to save to

    Returns:
    response

    """
    data = clean_data_strings(data)
    try:
        response = table.put_item(
            Item={
                USERID: id,
                DATA: data,
                TIMESTAMP: datetime.utcnow().isoformat()
            }
        )
    except ClientError as e:
        error_msg = e.response['Error']['Message']
        print("WARNING: error in put_dbdata:", error_msg)
        # if error_msg == "Requested resource not found":
        # no table TODO: make this work
        return e.response['Error']['Message']
    else:
        print("PutItem succeeded: " + id[0:PRINT_LIMIT])
        return response


def make_dynamodb_table(name):
    """Return a new DynamoDB table."""
    return DYNAMODB.create_table(
        TableName=name,
        KeySchema=[
            {
                'AttributeName': 'userId',
                'KeyType': 'HASH'
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'userId',
                'AttributeType': 'S'
            },

        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )


# --------------- speech response handlers -----------------
# build the json responses
# https://developer.amazon.com/public/solutions/alexa/alexa-skills-kit/docs/alexa-skills-kit-interface-reference
# response text cannot exceed 8000 characters
# response size cannot exceed 24 kilobytes

def tell_response(output):
    """Create a simple json tell response."""
    return {
        'outputSpeech': {
            'type': 'SSML',
            'ssml': "<speak>" + output + "</speak>"
        },
        'shouldEndSession': True
    }


def ask_response(output, reprompt):
    """Create a json ask response."""
    return {
        'outputSpeech': {
            'type': 'SSML',
            'ssml': "<speak>" + output + "</speak>"
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'SSML',
                'ssml': "<speak>" + reprompt + "</speak>"
            }
        },
        'shouldEndSession': False
    }


def add_directive(response, directive):
    """Append directive to response field in response."""
    if not directive:
        return response
    if 'directives' not in response:
        response['directives'] = []
    response['directives'].append(directive)
    print("DEBUG: add_directive", directive)
    return response


def service_response(event, response):
    """Create a simple json response.

    uses one of the speech_responses (`tell_response`, `ask_response`)
    can also create response from `add_directive`
    returns json for an Alexa service response
    """
    attributes = get_attributes(event)
    userId = get_userId(event)
    now = datetime.utcnow().isoformat()
    attributes[RESPONSE_TIME] = now
    attributes[SPEECHOUTPUT] = response['outputSpeech']['ssml']
    if response['shouldEndSession']:
        attributes[EXIT_TIME] = now
        session_length = datetime.fromisoformat(now) - datetime.fromisoformat(attributes[LAUNCH_TIME]) # noqa
        if session_length.total_seconds() > attributes[MAX_SESSION_TIME]:
            attributes[MAX_SESSION_TIME] = session_length.total_seconds()
        print(f"Exit thru stop with {attributes} at {now}")
        print(f"total duration: {session_length}")
    else:
        response_duration = datetime.fromisoformat(now) - datetime.fromisoformat(attributes[ENTRY_TIME]) # noqa
        if response_duration / timedelta(milliseconds=1) > attributes[MAX_RESPONSE_TIME]: # noqa
            attributes[MAX_RESPONSE_TIME] = response_duration / timedelta(milliseconds=1) # noqa
        print(f"Response duration: {response_duration}")
        if 'reprompt' in response:
            attributes[REPROMPT] = response['reprompt']['outputSpeech']['ssml']
    put_dbdata(DB_TABLE, userId, attributes)
    return {
        'version': '1.0',
        'sessionAttributes': attributes,
        'response': response
    }
