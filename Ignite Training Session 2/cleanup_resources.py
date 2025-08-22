#!/usr/bin/env python

"""
AWS Resource Cleanup Script

Deletes AWS resources including Bedrock knowledge bases and S3 buckets.

This script automates the cleanup of AWS resources by:
1. Deleting all Bedrock knowledge bases in the configured region
2. Removing S3 buckets that match a specific prefix pattern

Environment Variables:
    AWS_REGION (str): AWS region to target (defaults to us-west-2)

Requirements:
    - boto3 library
    - AWS credentials with appropriate permissions
    - IAM permissions for Bedrock and S3 operations

Usage:
    python cleanup.py
"""    

import boto3
import os

# Get AWS region from environment variable
region = os.environ.get('AWS_REGION', 'us-west-2')

# Initialize clients
bedrock = boto3.client('bedrock-agent', region_name=region)
s3 = boto3.client('s3', region_name=region)


def delete_all_knowledgebases():
    """
    Delete all Bedrock knowledge bases in the configured region.

    Lists and deletes each knowledge base found in the specified AWS region.
    Prints status messages for each deletion attempt.

    Returns:
        None

    Raises:
        Exception: If deletion of a knowledge base fails
    """    

    kb_response = bedrock.list_knowledge_bases()
    for kb in kb_response['knowledgeBaseSummaries']:
        confirm = input(f"Are you sure you want to delete knowledge base: {kb['name']} ({kb['knowledgeBaseId']})? [y/N]: ")
        if confirm.lower() != 'y':
            print(f"Skipping deletion of knowledge base: {kb['name']}")
            continue
            
        print(f"Deleting knowledge base: {kb['name']} ({kb['knowledgeBaseId']})")
        try:
            bedrock.delete_knowledge_base(knowledgeBaseId=kb['knowledgeBaseId'])
            print(f"Successfully deleted knowledge base: {kb['name']}")
        except Exception as e:
            print(f"Failed to delete knowledge base {kb['name']}: {str(e)}")


def delete_lab_s3_buckets(bucket_prefix):
    """
    Delete S3 buckets matching the specified prefix.

    Performs the following steps:
    1. Lists all S3 buckets in the AWS account
    2. Filters for buckets starting with the given prefix
    3. For matching buckets:
        - Removes all objects within the bucket
        - Deletes the empty bucket
    4. Skips non-matching buckets

    Args:
        bucket_prefix (str): Prefix to match bucket names against

    Returns:
        None

    Raises:
        Exception: If bucket deletion fails
    """    

    buckets = s3.list_buckets()
    for bucket in buckets['Buckets']:
        bucket_name = bucket['Name']
        if not bucket_name.startswith(bucket_prefix):
            print(f"Skipping bucket: {bucket_name}")
            continue

        confirm = input(f"Are you sure you want to delete bucket: {bucket_name}? [y/N]: ")
        if confirm.lower() != 'y':
            print(f"Skipping deletion of bucket: {bucket_name}")
            continue

        print(f"Deleting bucket: {bucket_name}")
        
        # Empty bucket first
        objects = s3.list_objects_v2(Bucket=bucket_name)
        if 'Contents' in objects:
            s3.delete_objects(
                Bucket=bucket_name,
                Delete={'Objects': [{'Key': obj['Key']} for obj in objects['Contents']]}
            )
        
        try:
            s3.delete_bucket(Bucket=bucket_name)
            print(f"Successfully deleted bucket: {bucket_name}")
        except Exception as e:
            print(f"Failed to delete bucket {bucket_name}: {str(e)}")


if __name__ == '__main__':
    delete_all_knowledgebases()
    delete_lab_s3_buckets('bedrock-kb-bucket-')
