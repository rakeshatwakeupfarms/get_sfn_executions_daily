# get_sfn_executions_daily

AWS Lambda for building the daily Step Functions automation report.

This replaces the data and formatting work previously handled by Make.com and Gemini. The Lambda now:

1. Finds executions that started during the current `Europe/Dublin` calendar day.
2. Extracts status, Dublin start time, execution ARN, state machine ARN, and customer ID.
3. Builds the WhatsApp-ready markdown table.
4. Returns `send_whatsapp_event`, shaped for the existing `send_whatsapp_message` Lambda.

## Environment Variables

- `AWS_REGION`: AWS region for Step Functions. Defaults to `eu-west-1`.
- `STATE_MACHINE_ARNS`: comma-separated Step Function ARNs. Defaults to `WakeupFarms_StepFunctions_v16-Bigquerygcp`.
- `REPORT_WATSAPP_NUMBER`: fallback WhatsApp chat/group ID for the report.
- `REPORT_WHATSAPP_NUMBER`: alternate spelling fallback for the report chat/group ID.

## Input

The Step Function can pass the WhatsApp group directly:

```json
{
  "watsapp_number": "120363xxxxxxxxxxxx@g.us"
}
```

If omitted, the Lambda uses `REPORT_WATSAPP_NUMBER` or `REPORT_WHATSAPP_NUMBER`.

## Output

The Lambda keeps the old `statusCode` and `body` fields for compatibility, but also returns the parsed fields at the top level for direct Step Functions use.

```json
{
  "statusCode": 200,
  "date": "2026-05-04",
  "timezone": "Europe/Dublin",
  "total_execution_count": 7,
  "failure_count": 0,
  "executions": [],
  "message": "| Status    | Start Time (Dublin Time)   | Customer ID |...",
  "send_whatsapp_event": {
    "watsapp_number": "120363xxxxxxxxxxxx@g.us",
    "message": "{\"alert\":\"| Status    | Start Time (Dublin Time)   | Customer ID |...\"}"
  }
}
```

## Permissions

The Lambda role needs:

- `states:ListExecutions`
- `states:DescribeExecution`

Limit both permissions to the reported state machine ARN(s) and their execution ARN patterns where possible.
