# get_sfn_executions_daily

This directory contains a Python AWS Lambda function designed to retrieve Step Functions (SFN) executions that started on the current day in Dublin time.

## Overview

The `lambda_function.py` script is an AWS Lambda function that fetches details of AWS Step Functions executions. It specifically looks for executions that started on the current day, based on Dublin time (IST = UTC+1). For each relevant execution, it retrieves the execution ARN, status, start date, and its input parameters. The function is configured to operate in the `eu-west-1` (Ireland) region and processes a predefined list of Step Function ARNs.

## Files

- `lambda_function.py`: The core Python script containing the Lambda function logic.
- `requirements.txt`: Lists Python dependencies (`boto3`) for the Lambda function.

## Setup

To set up and deploy this Lambda function:

1.  **Prerequisites**:
    *   An AWS account with appropriate permissions to create Lambda functions, IAM roles, and access AWS Step Functions.
    *   AWS CLI configured.
    *   Python 3.x environment.

2.  **Install Dependencies**:
    Create a `requirements.txt` file in this directory with `boto3` as a dependency:
    ```
    boto3
    ```
    Then, install the dependencies into a deployment package:
    ```bash
    pip install -r requirements.txt -t .
    ```
    After installation, zip the `lambda_function.py` along with the installed dependencies.

3.  **Create Lambda Function**:
    *   Create an AWS Lambda function in the `eu-west-1` region, specifying Python 3.x as the runtime.
    *   Configure an IAM role with permissions to invoke `states:ListExecutions` and `states:DescribeExecution` actions on the specified Step Functions.
    *   Upload the zipped deployment package (containing `lambda_function.py` and `boto3`).

4.  **Configure Environment Variables**:
    The function uses `eu-west-1` as the default region. If you need to override this, set an environment variable `AWS_REGION` in your Lambda configuration.

5.  **Trigger Configuration**:
    Configure a trigger for the Lambda function, such as an Amazon EventBridge (CloudWatch Events) rule to run daily. The function is designed to run once a day to check for executions from the current day in Dublin time.

## Usage

When triggered (e.g., daily by EventBridge), the Lambda function will:

1.  Determine the start and end times for the current day in Dublin (IST = UTC+1).
2.  Iterate through a hardcoded list of Step Function ARNs.
3.  For each ARN, list all executions that started within the calculated Dublin day.
4.  For each matching execution, retrieve its full details, including the input payload.
5.  Return a JSON response containing:
    *   The current date.
    *   The total count of executions found.
    *   Executions grouped by their state machine ARN, including their `executionArn`, `status`, `startDate`, and `input`.

### Example Output Structure:

```json
{
  "statusCode": 200,
  "body": "{\n  \"date\": \"2025-07-11\",\n  \"total_execution_count\": 1,\n  \"executions_by_machine\": {\n    \"arn:aws:states:eu-west-1:750014326377:stateMachine:WakeupFarms_StepFunctions_v15-Bigquerygcp\": {\n      \"execution_count\": 1,\n      \"executions\": [\n        {\n          \"executionArn\": \"arn:aws:states:eu-west-1:750014326377:execution:my-execution-id\",\n          \"status\": \"SUCCEEDED\",\n          \"startDate\": \"2025-07-11T10:00:00.000Z\",\n          \"input\": \"{\\\"key\\\":\\\"value\\\"}\",\n          \"stateMachineArn\": \"arn:aws:states:eu-west-1:750014326377:stateMachine:WakeupFarms_StepFunctions_v15-Bigquerygcp\"\n        }\n      ]\n    }\n  }\n}"
}
```
```
