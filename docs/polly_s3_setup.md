# Setting Up Amazon S3 for Polly Long Audio Files

This guide explains how to set up an Amazon S3 bucket for use with Amazon Polly's asynchronous text-to-speech (TTS) functionality.

## Why S3 is Needed

Amazon Polly's synchronous `SynthesizeSpeech` API has a 3000 character limit, which is often too small for podcast scripts. For longer texts (up to 100,000 billable or 200,000 total characters), Amazon Polly offers asynchronous synthesis via the `StartSpeechSynthesisTask` API, which requires an S3 bucket to store the generated audio.

## Setting Up an S3 Bucket

1. **Sign in to the AWS Management Console**:
   - Go to [AWS Console](https://console.aws.amazon.com/)
   - Sign in with the same AWS account you're using for Amazon Polly

2. **Navigate to S3**:
   - Search for "S3" in the search bar
   - Click on "S3" to open the S3 dashboard

3. **Create a New Bucket**:
   - Click "Create bucket"
   - Choose a unique bucket name (e.g., "mlb-podcast-audio")
   - Select the same AWS Region as set in your `.env` file
   - Keep other settings at their defaults
   - Click "Create bucket"

4. **Configure Bucket Permissions**:
   - Click on your new bucket
   - Navigate to the "Permissions" tab
   - Ensure "Block all public access" is enabled (for security)
   - Under "Bucket Policy", you can add a policy to allow Polly access:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowPollyToStoreAudio",
            "Effect": "Allow",
            "Principal": {
                "Service": "polly.amazonaws.com"
            },
            "Action": [
                "s3:PutObject"
            ],
            "Resource": "arn:aws:s3:::YOUR-BUCKET-NAME/*",
            "Condition": {
                "StringEquals": {
                    "aws:SourceAccount": "YOUR-AWS-ACCOUNT-ID"
                }
            }
        }
    ]
}
```

## IAM Setup

Ensure your IAM user or role has permissions for both Polly and S3:

1. **Navigate to IAM**:
   - In the AWS Console, search for "IAM"
   - Click on "IAM" to open the IAM dashboard

2. **Add Required Permissions**:
   - Find your user or create a new one
   - Attach the following policies:
     - `AmazonPollyFullAccess`
     - `AmazonS3FullAccess` (or a more restrictive policy that allows access to only your specific bucket)

## Update Your Configuration

1. **Edit your `.env` file**:
   - Add your S3 bucket name:
   ```
   AWS_S3_BUCKET=your-bucket-name
   ```

2. **Test the setup**:
   - Run the test script:
   ```
   python test_polly.py
   ```
   - If successful, you should see both tests pass, with the long text using the asynchronous API

## Troubleshooting

If you encounter issues:

1. **Check S3 Permissions**:
   - Ensure your IAM user has permissions to:
     - Create objects in the S3 bucket
     - Start speech synthesis tasks in Polly
     - Get objects from the S3 bucket

2. **Check Region Consistency**:
   - Make sure your S3 bucket and Polly are in the same AWS region

3. **Check S3 Bucket Name**:
   - Verify your bucket name is correctly specified in the `.env` file
   - Ensure the bucket exists and is accessible to your IAM user

4. **Review CloudTrail Logs**:
   - If available, check CloudTrail logs for permission errors 