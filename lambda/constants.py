"""constants.py: constants for lambda tone therapy skill."""
PRINT_LIMIT = 33    # to shorten debug output

# --------------- context keys -----------------
# CONTEXT keys, values don't matter but must be consistent in code
START_STATE = 'start state'

# --------------- intent names -----------------
# must match the names in model.json on Alexa service
GO_INTENT = 'GoIntent'

# --------------- slots names -----------------
# must match the name of the slot in model.json on Alexa service

# --------------- attributes keys -----------------
# labels for Attribute keys, values don't matter but can't change unless
#   you update names in the database.  Should all be unique.
SPEECHOUTPUT = 'speechOutput'
REPROMPT = 'repromptText'
VISIT_COUNT = 'number of visits'
STATE = 'conversation state'
LAUNCH_TIME = 'launch time'
ENTRY_TIME = 'lambda handler entry time'
RESPONSE_TIME = 'time sent response'
EXIT_TIME = 'time session ended'
MAX_RESPONSE_TIME = 'max time to respond'
MAX_SESSION_TIME = 'max length of session'

# --------------- DynamoDB names -----------------
USERID = 'userId'   # table key
DATA = 'data'       # table record
TIMESTAMP = 'timestamp'       # table record

# --------------- services -----------------
DB_TABLE_NAME = 'GoTable'

# --------------- speech -----------------
SHORT_PAUSE = "<break time='1s'/> "

VOCAB = {
    'en-US': {
        'messages': {
            'HELP_MESSAGE': "I can't help you. ",
            'STOP_MESSAGE': "Ok. Goodbye! ",
            'FALLBACK_MESSAGE': "I'm sorry, I don't understand what you want. "
                                "Try again. ",
            'FALLBACK_REPROMPT': "Please try asking that a different way. ",
            'BAD_PROBLEM': "I'm sorry, something happened that shouldn't "
                           "have. Please Try again. ",
        }
    },
}
