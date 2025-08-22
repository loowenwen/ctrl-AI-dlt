#!/usr/bin/env python

"""
This script creates a basic guardrail configuration for Amazon Bedrock based on the boto3 documentation:
https://boto3.amazonaws.com/v1/documentation/api/1.35.9/reference/services/bedrock/client/create_guardrail.html

The guardrail includes policies for:
- Topic filtering (protected characteristics, illegal activities, financial/health/legal advice)
- Content filtering (sexual, violence, hate speech, insults, misconduct, prompt attacks)
- Word filtering (profanity)
- Sensitive information handling (PII like emails, phone numbers, names, credit card numbers)
- Contextual grounding (relevance and grounding thresholds)
"""

import boto3
import json
import os

region = os.getenv('AWS_REGION', 'us-west-2')
bedrock = boto3.client('bedrock', region_name=region)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)

TOPICSCONFIG = [
        {
            'name': 'Protected characteristics discrimination',
            'definition': 'Discrimination based on age, religion, race, or gender, including refusing services, employment, housing, or differential treatment based on these protected characteristics',
            'type': 'DENY'
        },
        {
            'name': 'Activities that are illegal in most countries',
            'definition': 'Promoting or facilitating activities that are illegal in most countries',
            'type': 'DENY'
        },
        {
            'name': 'Financial advice guardrail',
            'definition': 'Restricting specific financial advice that could be harmful, misleading, or requires professional licensing, including investment recommendations, tax avoidance strategies, or guaranteed returns',
            'examples': [
                'You should invest all your savings in this specific cryptocurrency',
                'This stock will definitely double in value next month',
                'This investment strategy guarantees 20% annual returns with no risk',
                'Detailed instructions for complex tax avoidance schemes'
            ],
            'type': 'DENY'
        },
        {
            'name': 'Health advice guardrail',
            'definition': 'Restricting specific health and medical advice that could be harmful, misleading, or requires professional medical licensing, including diagnosis, treatment recommendations, or medication guidance',
            'examples': [
                'This herbal supplement will cure your cancer',
                'You don\'t need vaccines because natural immunity is better',
                'Claims of miracle cures or treatments without scientific evidence'
            ],
            'type': 'DENY'
        },
        {
            'name': 'Legal advice guardrail',
            'definition': 'Restricting specific legal advice that requires professional licensing, could be harmful, or misleading, including case-specific guidance, document preparation, or legal strategies',
            'type': 'DENY'
        }
    ]

FILTERSCONFIG = [
        {
            'type': 'SEXUAL',
            'inputStrength': 'HIGH',
            'outputStrength': 'HIGH'
        },
        {
            'type': 'VIOLENCE',
            'inputStrength': 'HIGH',
            'outputStrength': 'HIGH'
        },
        {
            'type': 'HATE',
            'inputStrength': 'HIGH',
            'outputStrength': 'HIGH'
        },
        {
            'type': 'INSULTS',
            'inputStrength': 'HIGH',
            'outputStrength': 'HIGH'
        },
        {
            'type': 'MISCONDUCT',
            'inputStrength': 'HIGH',
            'outputStrength': 'HIGH'
        },
        {
            'type': 'PROMPT_ATTACK',
            'inputStrength': 'HIGH',
            'outputStrength': 'NONE'
        }
    ]

SENSITIVE_WORDS_CONFIG = {
        'piiEntitiesConfig': [
            {'type': 'EMAIL', 'action': 'ANONYMIZE'},
            {'type': 'PHONE', 'action': 'ANONYMIZE'},
            {'type': 'NAME', 'action': 'ANONYMIZE'},
            {'type': 'CREDIT_DEBIT_CARD_NUMBER', 'action': 'BLOCK'}
        ]
    }

def create_guardrail(guardrail_name):
    """
    Create a guardrail
    """
    response = bedrock.create_guardrail(
        name=guardrail_name,
        description='Basic Bedrock Guardrail',
        topicPolicyConfig={
            'topicsConfig': TOPICSCONFIG
        },
        contentPolicyConfig={
            'filtersConfig': FILTERSCONFIG
        },
        wordPolicyConfig={
            'managedWordListsConfig': [
                {'type': 'PROFANITY'}
            ]
        },
        sensitiveInformationPolicyConfig = SENSITIVE_WORDS_CONFIG,
        contextualGroundingPolicyConfig={
            'filtersConfig': [
                {
                    'type': 'GROUNDING',
                    'threshold': 0.75
                },
                {
                    'type': 'RELEVANCE',
                    'threshold': 0.75
                }
            ]
        },
        blockedInputMessaging="""Sorry, the model cannot answer this question. """,
        blockedOutputsMessaging="""Sorry, the model cannot answer this question. """
    )
    return response


def main():
    response = create_guardrail('basic-bedrock-guardrail')
    print(json.dumps(response, indent=2, default=str))
    guardrail_id = response['guardrailId']
    print(f'Your Guardrail ID is: {guardrail_id}')


if __name__ == '__main__':
    main()
