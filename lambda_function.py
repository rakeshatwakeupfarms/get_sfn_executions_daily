import boto3
from datetime import datetime, timedelta, timezone
import os
import json


def get_executions_today_dublin_with_input(state_machine_arn):
    """
    Retrieves Step Function executions that started on the current day in Dublin time,
    including their input parameters.

    Args:
        state_machine_arn (str): The ARN of the Step Function state machine.

    Returns:
        list: A list of execution details (dictionaries) that started today in Dublin,
              including 'executionArn', 'status', 'startDate', and 'input'.
    """
    client = boto3.client(
        "stepfunctions", region_name=os.environ.get("AWS_REGION") or "eu-west-1"
    )

    # Get the current time in Dublin (IST = UTC+1)
    dublin_timezone = timezone(timedelta(hours=1))
    now_dublin = datetime.now(dublin_timezone)

    # Calculate the start and end of the current day in Dublin
    start_of_day_dublin = now_dublin.replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_day_dublin = start_of_day_dublin + timedelta(days=1)

    # Convert Dublin times to UTC
    utc_offset = timedelta(hours=1)
    start_of_day_utc = start_of_day_dublin - utc_offset
    end_of_day_utc = end_of_day_dublin - utc_offset

    paginator = client.get_paginator("list_executions")
    executions_today_with_input = []

    try:
        for page in paginator.paginate(stateMachineArn=state_machine_arn):
            for execution in page["executions"]:
                start_time_utc = execution["startDate"].replace(tzinfo=timezone.utc)
                if start_of_day_utc <= start_time_utc < end_of_day_utc:
                    # Call describe_execution to get input details
                    execution_details = client.describe_execution(
                        executionArn=execution["executionArn"]
                    )
                    executions_today_with_input.append(
                        {
                            "executionArn": execution["executionArn"],
                            "status": execution["status"],
                            "startDate": str(execution["startDate"]),
                            "input": execution_details.get("input"),
                            "stateMachineArn": state_machine_arn,  # Add state machine ARN to identify source
                        }
                    )

        return executions_today_with_input

    except Exception as e:
        print(f"Error getting executions for {state_machine_arn}: {str(e)}")
        return []


def lambda_handler(event, context):
    """
    AWS Lambda handler function.
    """
    try:
        # List of state machine ARNs to check
        state_machine_arns = [
            "arn:aws:states:eu-west-1:518923560508:stateMachine:WakeupFarms_StepFunctions_v11_auto-retry",
            "arn:aws:states:eu-west-1:518923560508:stateMachine:WakeupFarms_StepFunctions_v12_weath",
        ]

        # Get executions from all state machines
        all_executions = []
        for arn in state_machine_arns:
            executions = get_executions_today_dublin_with_input(arn)
            all_executions.extend(executions)

        current_date = datetime.now(timezone(timedelta(hours=1))).strftime("%Y-%m-%d")

        if all_executions:
            # Group executions by state machine
            executions_by_machine = {}
            for execution in all_executions:
                arn = execution["stateMachineArn"]
                if arn not in executions_by_machine:
                    executions_by_machine[arn] = []
                executions_by_machine[arn].append(execution)

            response_body = {
                "date": current_date,
                "total_execution_count": len(all_executions),
                "executions_by_machine": {
                    arn: {"execution_count": len(execs), "executions": execs}
                    for arn, execs in executions_by_machine.items()
                },
            }
        else:
            response_body = {
                "date": current_date,
                "message": "No executions found for any state machine for the current day",
                "executions_by_machine": {},
            }

        return {"statusCode": 200, "body": json.dumps(response_body, indent=2)}

    except Exception as e:
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
