import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import boto3


DEFAULT_STATE_MACHINE_ARNS = [
    "arn:aws:states:eu-west-1:750014326377:stateMachine:WakeupFarms_StepFunctions_v16-Bigquerygcp"
]
DUBLIN_TZ = ZoneInfo("Europe/Dublin")


def get_state_machine_arns():
    configured_arns = os.environ.get("STATE_MACHINE_ARNS")
    if not configured_arns:
        return DEFAULT_STATE_MACHINE_ARNS

    return [arn.strip() for arn in configured_arns.split(",") if arn.strip()]


def get_dublin_day_window(now=None):
    now_dublin = now.astimezone(DUBLIN_TZ) if now else datetime.now(DUBLIN_TZ)
    start_dublin = now_dublin.replace(hour=0, minute=0, second=0, microsecond=0)
    end_dublin = start_dublin + timedelta(days=1)

    return start_dublin, end_dublin


def parse_execution_input(execution_input):
    if not execution_input:
        return {}

    if isinstance(execution_input, dict):
        return execution_input

    try:
        return json.loads(execution_input)
    except (TypeError, json.JSONDecodeError):
        return {}


def extract_customer_id(execution_input):
    parsed_input = parse_execution_input(execution_input)
    return (
        parsed_input.get("customerid")
        or parsed_input.get("customer_id")
        or parsed_input.get("customerId")
        or "UNKNOWN"
    )


def format_dublin_time(value):
    return value.astimezone(DUBLIN_TZ).strftime("%Y-%m-%d %H:%M:%S")


def get_executions_for_dublin_day(state_machine_arn, start_dublin, end_dublin):
    print(f"Fetching executions for state machine: {state_machine_arn}")
    client = boto3.client(
        "stepfunctions", region_name=os.environ.get("AWS_REGION") or "eu-west-1"
    )

    paginator = client.get_paginator("list_executions")
    executions = []

    for page in paginator.paginate(stateMachineArn=state_machine_arn):
        print(f"Found {len(page.get('executions', []))} executions in current page")

        for execution in page.get("executions", []):
            start_time = execution["startDate"]
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)

            start_time_dublin = start_time.astimezone(DUBLIN_TZ)

            if start_time_dublin >= end_dublin:
                continue

            if start_time_dublin < start_dublin:
                return executions

            execution_details = client.describe_execution(
                executionArn=execution["executionArn"]
            )
            execution_input = execution_details.get("input")

            executions.append(
                {
                    "executionArn": execution["executionArn"],
                    "stateMachineArn": state_machine_arn,
                    "status": execution["status"],
                    "startDate": start_time.isoformat(),
                    "startTimeDublin": format_dublin_time(start_time),
                    "customerId": str(extract_customer_id(execution_input)),
                    "input": execution_input,
                }
            )

    return executions


def build_report_message(executions):
    if not executions:
        return (
            "| Status    | Start Time (Dublin Time)   | Customer ID |\n"
            "|-----------|-----------------------------|-------------|\n\n"
            "There were no executions found for today.\n\n"
            "These are the automation runs for today."
        )

    sorted_executions = sorted(
        executions, key=lambda item: item["startTimeDublin"], reverse=True
    )

    lines = [
        "| Status    | Start Time (Dublin Time)   | Customer ID |",
        "|-----------|-----------------------------|-------------|",
    ]

    for execution in sorted_executions:
        lines.append(
            f"| {execution['status']:<9} | {execution['startTimeDublin']:<27} | {execution['customerId']:<11} |"
        )

    failed_executions = [
        execution
        for execution in sorted_executions
        if execution["status"] not in {"SUCCEEDED"}
    ]

    lines.append("")
    if failed_executions:
        if len(failed_executions) == 1:
            lines.append("There was 1 failure in the executions.")
        else:
            lines.append(
                f"There were {len(failed_executions)} failures in the executions."
            )
    else:
        lines.append("There were no failures in the executions.")

    lines.append("")
    lines.append("These are the automation runs for today.")

    return "\n".join(lines)


def lambda_handler(event, context):
    try:
        event = event or {}
        state_machine_arns = get_state_machine_arns()
        start_dublin, end_dublin = get_dublin_day_window()

        print(
            "Searching for executions between Dublin times: "
            f"{start_dublin.isoformat()} and {end_dublin.isoformat()}"
        )
        print(f"Starting execution check for {len(state_machine_arns)} state machines")

        all_executions = []
        for arn in state_machine_arns:
            all_executions.extend(
                get_executions_for_dublin_day(arn, start_dublin, end_dublin)
            )

        message = build_report_message(all_executions)
        report_watsapp_number = (
            event.get("watsapp_number")
            or event.get("whatsapp_number")
            or os.environ.get("REPORT_WATSAPP_NUMBER")
            or os.environ.get("REPORT_WHATSAPP_NUMBER")
        )

        response_body = {
            "date": start_dublin.strftime("%Y-%m-%d"),
            "timezone": "Europe/Dublin",
            "total_execution_count": len(all_executions),
            "failure_count": sum(
                1 for execution in all_executions if execution["status"] != "SUCCEEDED"
            ),
            "executions": sorted(
                all_executions,
                key=lambda item: item["startTimeDublin"],
                reverse=True,
            ),
            "message": message,
            "send_whatsapp_event": {
                "watsapp_number": report_watsapp_number,
                "message": json.dumps({"alert": message}),
            },
        }

        return {
            "statusCode": 200,
            "body": json.dumps(response_body, indent=2),
            **response_body,
        }

    except Exception as e:
        print(f"Error in lambda_handler: {str(e)}")
        return {"statusCode": 500, "body": json.dumps({"error": str(e)})}
