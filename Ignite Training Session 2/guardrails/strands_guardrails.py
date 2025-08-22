#!/usr/bin/env python

import boto3
import json
import os

from strands import Agent
from strands.models import BedrockModel


region = os.getenv('AWS_REGION', 'us-west-2')
bedrock = boto3.client('bedrock', region_name=region)
bedrock_runtime = boto3.client('bedrock-runtime', region_name=region)


def list_guardrail_ids():
    response = bedrock.list_guardrails()
    guardrails = response.get('guardrails', [])
    if len(guardrails) > 0:
        for guardrail in guardrails:
            id = guardrail['id']
            name = guardrail['name']
            print(f'Guardrail ID: {id}, Name: {name}')
        return [ guardrail['id'] for guardrail in guardrails ]
    else:
        return []


def main(guardrail_id):
    # Create a Bedrock model with guardrail configuration
    bedrock_model = BedrockModel(
        model_id = "us.amazon.nova-micro-v1:0",
        guardrail_id = guardrail_id,         # Your Bedrock guardrail ID
        guardrail_version = "DRAFT",         # Guardrail version
        guardrail_trace = "enabled",         # Options: "enabled", "disabled", "enabled_full"
        guardrail_stream_processing_mode="sync",  # Options: "sync", "async"
        guardrail_redact_input=True,         # Default: True
        guardrail_redact_input_message="[model input blocked by guardrail]",  # Default: [User input redacted.]
        guardrail_redact_output=False,       # Default: False
        guardrail_redact_output_message="[model output blocked by guardrail]" # Default: [Assistant output redacted.]
    )

    # Create agent with the guardrail-protected model
    agent = Agent(
        system_prompt="You are a helpful assistant.",
        model=bedrock_model,
    )

    # Use the protected agent for conversations
    prompts = [
        "How can I make millions from crypto?",
        "Recommend me some health supplements that will cure cancer"
    ]
    
    for prompt in prompts:
        print('-' * 80)
        print(f'**Question**: {prompt}')
        print(f'**Response**:')
        response = agent(prompt)

        # Handle potential guardrail interventions
        if response.stop_reason == "guardrail_intervened":
            print("\nContent was blocked by guardrails, conversation context overwritten!")

        print(f"\nConversation: {json.dumps(agent.messages, indent=4)}\n")


guardrail_ids = list_guardrail_ids()

if __name__ == '__main__':
    if len(guardrail_ids):
        main(guardrail_ids[0])
    else:
        print('No guardrails found. Please create a guardrail first.')
