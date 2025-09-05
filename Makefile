REGION ?= us-east-1
# auto-detect account if not provided (requires AWS CLI configured)
ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text 2>/dev/null)
REPO_BUDGET ?= ctrl-ai-dlt/bto-budget
REPO_COST ?= ctrl-ai-dlt/bto-cost
ROLE_NAME ?= bedrock-lambda-role
BEDROCK_POLICY_NAME ?= BedrockInvokePolicy
# Optional: set ARCH=arm64 (Apple Silicon) or ARCH=x86_64
ARCH ?=
# Map ARCH to Docker platform (default to linux/amd64 if not set)
PLATFORM := $(if $(ARCH),linux/$(ARCH),linux/amd64)

ECR_BUDGET := $(ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com/$(REPO_BUDGET)
ECR_COST := $(ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com/$(REPO_COST)

.PHONY: ecr-create login-ecr build-budget push-budget build-cost push-cost \
        build-budget-nocache push-budget-nocache build-cost-nocache push-cost-nocache \
        push-budget-buildx push-cost-buildx \
        lambda-create-budget lambda-create-cost lambda-update-budget lambda-update-cost \
        lambda-ensure-budget lambda-ensure-cost \
        invoke-budget invoke-cost iam-bootstrap iam-inline-policy \
        url-budget url-cost print-url-budget print-url-cost setup-budget setup-cost \
        deploy-budget-all deploy-cost-all

ecr-create:
	aws ecr create-repository --repository-name $(REPO_BUDGET) --region $(REGION) || true
	aws ecr create-repository --repository-name $(REPO_COST) --region $(REGION) || true

login-ecr:
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com

build-budget:
	docker build -t bto-budget -f deploy/Dockerfile.budget .

push-budget: build-budget
	docker tag bto-budget:latest $(ECR_BUDGET):latest
	docker push $(ECR_BUDGET):latest

build-cost:
	docker build -t bto-cost -f deploy/Dockerfile.cost .

push-cost: build-cost
	docker tag bto-cost:latest $(ECR_COST):latest
	docker push $(ECR_COST):latest

# No-cache variants (useful to avoid ECR cross-mount 404s)
build-budget-nocache:
	docker build --no-cache -t bto-budget -f deploy/Dockerfile.budget .

push-budget-nocache: build-budget-nocache
	docker tag bto-budget:latest $(ECR_BUDGET):latest
	docker push $(ECR_BUDGET):latest

build-cost-nocache:
	docker build --no-cache -t bto-cost -f deploy/Dockerfile.cost .

push-cost-nocache: build-cost-nocache
	docker tag bto-cost:latest $(ECR_COST):latest
	docker push $(ECR_COST):latest

# Buildx + gzip-compressed layer push (works around Lambda media-type issues)
push-budget-buildx:
	# Ensure a buildx builder exists
	-docker buildx create --use >/dev/null 2>&1 || true
	docker buildx build \
	  --platform $(PLATFORM) \
	  -f deploy/Dockerfile.budget \
	  -t $(ECR_BUDGET):latest \
	  --provenance=false --sbom=false \
	  --output type=image,compression=gzip \
	  --push \
	  .

push-cost-buildx:
	# Ensure a buildx builder exists
	-docker buildx create --use >/dev/null 2>&1 || true
	docker buildx build \
	  --platform $(PLATFORM) \
	  -f deploy/Dockerfile.cost \
	  -t $(ECR_COST):latest \
	  --provenance=false --sbom=false \
	  --output type=image,compression=gzip \
	  --push \
	  .

lambda-create-budget:
	aws lambda create-function \
	  --function-name bto-budget-estimator \
	  --package-type Image \
	  --code ImageUri=$(ECR_BUDGET):latest \
	  --role arn:aws:iam::$(ACCOUNT_ID):role/$(ROLE_NAME) \
	  --region $(REGION) \
	  --timeout 30 \
	  --memory-size 512 \
	  $(if $(ARCH),--architectures $(ARCH),)

lambda-create-cost:
	aws lambda create-function \
	  --function-name bto-cost-estimator \
	  --package-type Image \
	  --code ImageUri=$(ECR_COST):latest \
	  --role arn:aws:iam::$(ACCOUNT_ID):role/$(ROLE_NAME) \
	  --region $(REGION) \
	  --timeout 60 \
	  --memory-size 2048 \
	  $(if $(ARCH),--architectures $(ARCH),)

lambda-update-budget:
	aws lambda update-function-code \
	  --function-name bto-budget-estimator \
	  --image-uri $(ECR_BUDGET):latest \
	  --region $(REGION)

lambda-update-cost:
	aws lambda update-function-code \
	  --function-name bto-cost-estimator \
	  --image-uri $(ECR_COST):latest \
	  --region $(REGION)

# Create if missing, else update (budget)
lambda-ensure-budget:
	@if aws lambda get-function --function-name bto-budget-estimator --region $(REGION) >/dev/null 2>&1; then \
	  echo "Updating existing function bto-budget-estimator"; \
	  aws lambda update-function-code --function-name bto-budget-estimator --image-uri $(ECR_BUDGET):latest --region $(REGION); \
	else \
	  echo "Creating function bto-budget-estimator"; \
	  aws lambda create-function --function-name bto-budget-estimator --package-type Image --code ImageUri=$(ECR_BUDGET):latest --role arn:aws:iam::$(ACCOUNT_ID):role/$(ROLE_NAME) --region $(REGION) --timeout 30 --memory-size 512 $(if $(ARCH),--architectures $(ARCH),); \
	fi

# Create if missing, else update (cost)
lambda-ensure-cost:
	@if aws lambda get-function --function-name bto-cost-estimator --region $(REGION) >/dev/null 2>&1; then \
	  echo "Updating existing function bto-cost-estimator"; \
	  aws lambda update-function-code --function-name bto-cost-estimator --image-uri $(ECR_COST):latest --region $(REGION); \
	else \
	  echo "Creating function bto-cost-estimator"; \
	  aws lambda create-function --function-name bto-cost-estimator --package-type Image --code ImageUri=$(ECR_COST):latest --role arn:aws:iam::$(ACCOUNT_ID):role/$(ROLE_NAME) --region $(REGION) --timeout 60 --memory-size 2048 $(if $(ARCH),--architectures $(ARCH),); \
	fi

# --- IAM bootstrap (trust + policies) ---
iam-bootstrap:
	# Create or update trust policy to allow Lambda to assume role
	@if aws iam get-role --role-name $(ROLE_NAME) >/dev/null 2>&1; then \
	  echo "Role $(ROLE_NAME) exists. Updating trust policy..." ; \
	  aws iam update-assume-role-policy --role-name $(ROLE_NAME) --policy-document file://deploy/iam-trust.json ; \
	else \
	  echo "Creating role $(ROLE_NAME)..." ; \
	  aws iam create-role --role-name $(ROLE_NAME) --assume-role-policy-document file://deploy/iam-trust.json >/dev/null ; \
	fi
	# Attach basic execution for CloudWatch Logs
	aws iam attach-role-policy --role-name $(ROLE_NAME) --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole || true
	# Create (or reuse) Bedrock invoke policy and attach to role
	@POLICY_ARN=$$(aws iam create-policy --policy-name $(BEDROCK_POLICY_NAME) --policy-document file://deploy/bedrock-policy.json --query Policy.Arn --output text 2>/dev/null || aws iam list-policies --scope Local --query "Policies[?PolicyName=='$(BEDROCK_POLICY_NAME)'].Arn | [0]" --output text); \
	echo "Using policy ARN: $$POLICY_ARN"; \
	aws iam attach-role-policy --role-name $(ROLE_NAME) --policy-arn $$POLICY_ARN || true
	@echo "IAM bootstrap complete for role $(ROLE_NAME)."

# Fallback: attach inline policy if managed policy creation is restricted
iam-inline-policy:
	aws iam put-role-policy --role-name $(ROLE_NAME) --policy-name Inline$(BEDROCK_POLICY_NAME) --policy-document file://deploy/bedrock-policy.json

# --- Function URLs with permissive CORS (dev only) ---
url-budget:
	aws lambda create-function-url-config \
	  --function-name bto-budget-estimator \
	  --auth-type NONE \
	  --cors 'AllowOrigins=["*"],AllowMethods=["POST","OPTIONS"],AllowHeaders=["*"]' \
	  --region $(REGION) || aws lambda update-function-url-config \
	  --function-name bto-budget-estimator \
	  --cors 'AllowOrigins=["*"],AllowMethods=["POST","OPTIONS"],AllowHeaders=["*"]' \
	  --region $(REGION)
	aws lambda add-permission \
	  --function-name bto-budget-estimator \
	  --action lambda:InvokeFunctionUrl \
	  --principal "*" \
	  --function-url-auth-type NONE \
	  --statement-id public-budget-url \
	  --region $(REGION) || true

url-cost:
	aws lambda create-function-url-config \
	  --function-name bto-cost-estimator \
	  --auth-type NONE \
	  --cors 'AllowOrigins=["*"],AllowMethods=["POST","OPTIONS"],AllowHeaders=["*"]' \
	  --region $(REGION) || aws lambda update-function-url-config \
	  --function-name bto-cost-estimator \
	  --cors 'AllowOrigins=["*"],AllowMethods=["POST","OPTIONS"],AllowHeaders=["*"]' \
	  --region $(REGION)
	aws lambda add-permission \
	  --function-name bto-cost-estimator \
	  --action lambda:InvokeFunctionUrl \
	  --principal "*" \
	  --function-url-auth-type NONE \
	  --statement-id public-cost-url \
	  --region $(REGION) || true

print-url-budget:
	aws lambda get-function-url-config --function-name bto-budget-estimator --query FunctionUrl --output text --region $(REGION)

print-url-cost:
	aws lambda get-function-url-config --function-name bto-cost-estimator --query FunctionUrl --output text --region $(REGION)

# Convenience: full setup for each function after image push
setup-budget: lambda-create-budget url-budget print-url-budget
setup-cost: lambda-create-cost url-cost print-url-cost

# Full pipeline: IAM + ECR + login + push (buildx) + ensure lambda + URL + print URL
deploy-budget-all: iam-bootstrap ecr-create login-ecr push-budget-buildx lambda-ensure-budget url-budget print-url-budget
deploy-cost-all: iam-bootstrap ecr-create login-ecr push-cost-buildx lambda-ensure-cost url-cost print-url-cost

invoke-budget:
	aws lambda invoke \
	  --function-name bto-budget-estimator \
	  --region $(REGION) \
	  --payload '{"household_income":9000,"cash_savings":20000,"cpf_savings":50000,"bto_price":350000}' \
	  response.json && cat response.json && echo

invoke-cost:
	aws lambda invoke \
	  --function-name bto-cost-estimator \
	  --region $(REGION) \
	  --payload '{"project_location":"queenstown","flat_type":"4-room","exercise_date":"2025-10-01"}' \
	  response.json && cat response.json && echo
