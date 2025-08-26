import boto3
import json

def list_bedrock_models():
    """List all available Bedrock models in your account"""
    try:
        # Create a session with your SSO profile
        session = boto3.Session(
            profile_name='myisb01_IsbUsersPS-371061166839',
            region_name='us-east-1'
        )
        
        # Create Bedrock client
        bedrock = session.client('bedrock')
        
        # List foundation models
        response = bedrock.list_foundation_models()
        
        # Pretty print the models
        print("\nAvailable Bedrock Models:")
        print("------------------------")
        for model in response['modelSummaries']:
            print(f"\nModel ID: {model['modelId']}")
            print(f"Model Name: {model.get('modelName', 'N/A')}")
            print(f"Provider: {model.get('providerName', 'N/A')}")
            print(f"Status: {model['modelLifecycle']['status']}")
            print("------------------------")
            
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    list_bedrock_models()