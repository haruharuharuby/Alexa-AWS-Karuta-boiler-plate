# -*- coding: utf-8 -*-
from __future__ import print_function

import os
import boto3
import logging
import json
import re
import random

dynamodb_client = boto3.client('dynamodb')


def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'SSML',
            'ssml': "<speak>%s</speak>" % (output)
        },
        'card': {
            'type': 'Simple',
            'title': title,
            'content': re.sub('<.*?>', '\n', output)
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'SSML',
                'ssml': "<speak>%s</speak>" % (reprompt_text)
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }



def more_twice_access(uid):
    uids = dynamodb_client.query(
        TableName='aws_karuta_users',
        KeyConditionExpression='user_id = :uid',
        ExpressionAttributeValues={":uid": {"S": uid}}
    )
    if uids['Count'] == 0:
        dynamodb_client.put_item(
            TableName='aws_karuta_users',
            Item={'user_id': {'S': uid}}
        )
        return False
    else:
        return True


def get_card():
    kid = random.randrange(100) + 1
    karuta = dynamodb_client.query(
        TableName='aws_karuta_data',
        KeyConditionExpression='karuta_id = :kid',
        ExpressionAttributeValues={":kid": {"S": kid}}
    )
    if karuta['Count'] > 0:
        return karuta['Items'][0]['karuta_text']['S']


def get_welcome_response(session=None):

    session_attributes = {}
    card_title = "Welcome to AWS Karuta Service"
    should_end_session = False

    if more_twice_access(session[u'user']['userId']):
        speech_output = reprompt_text = "Hello again. enjoy AWS Karuta!"
    else:
        speech_output = reprompt_text = "Hello. You can play AWS Karuta. Pleas call next card."

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "AWS Karuta"
    speech_output = "End to this skill"

    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))


# pass request['intent']['slots']['XXXX']
def is_match_slots(slot):
    if 'resolutions' in slot:
        return (slot['resolutions']['resolutionsPerAuthority'][0]['status']['code'] == 'ER_SUCCESS_MATCH')
    else:
        return True


def next_card(request, session):
    card_title = 'AWS Karuta next card'
    should_end_session = False
    session_attributes = session['attributes'] if 'attributes' in session else {}
    reprompt_text = "Please call next."

    karuta = get_card()
    if karuta:
        speech_output = karuta
    else:
        speech_output = "Please tell me again."

    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


def set_locale(request, session):
    card_title = 'set locale'
    should_end_session = False
    session_attributes = session['attributes'] if 'attributes' in session else {}

    if 'value' in request['intent']['slots']['locale']:
        locale = request['intent']['slots']['locale']['value']
    else:
        locale = ''

    if locale:
        speech_output = reprompt_text = "Set locale to %s" % (locale)
    else:
        speech_output = reprompt_text = "I could recognize locale. <break /> Please try again."

    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


def call_help(request, session):
    card_title = 'AWS Karuta Help'
    should_end_session = True
    session_attributes = session['attributes'] if 'attributes' in session else {}
    speech_output = reprompt_text = "This is AWS Karuta Service. You can say naxt. Alexa saids one of AWS Karuta. "
    return build_response(session_attributes, build_speechlet_response(card_title, speech_output, reprompt_text, should_end_session))


# --------------- Events ------------------

def on_session_started(session_started_request, session):
    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response(session)


def on_intent(intent_request, session):
    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    print(intent_name)

    # Dispatch to your skill's intent handlers
    if intent_name == "NextIntent":
        return next_card(intent_request, session)
    elif intent_name == "LocaleIntent":
        return set_locale(intent_request, session)
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    elif intent_name == "AMAZON.HelpIntent":
        return call_help(intent_request, session)
    else:
        raise ValueError("Invalid intent")


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


def lambda_handler(event, context):

    print(event)
    print(context)

    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']}, event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])
