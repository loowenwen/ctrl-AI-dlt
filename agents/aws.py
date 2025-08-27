# To get AWS credentials for a specific profile, you can use the AWS CLI command
aws sts get-caller-identity --profile myisb01_IsbUsersPS-371061166839

# Make sure to set the AWS_PROFILE environment variable in your shell
export AWS_PROFILE=myisb01_IsbUsersPS-371061166839

# Then run the agent script
python agents/agent.py