import os
import boto3
from requests import Request, Session
import urllib3
from botocore.exceptions import ClientError
import json
from package.get_secret import secret
import datetime

urllib3.disable_warnings()


class Iam:
    '''
    ALL CONNECTIVITY CODE HAS BEEN REMOVED FOR SECURITY REASONS. EXAMPLES CAN BE PROVIDED UPON REQUEST. I WOULD
    RECOMMEND ADDING IT HERE THOUGH. GOOD LUCK. ALSO NO TRY/EXCEPTS HAVE BEEN ADDED AS OF YET, AND CURRENT WORK-FLOW
    IS AS FOLLOWS - FIND OLD ACCESS KEYS > 90 DAYS OLD. MARK KEY AS INACTIVE. ADD NEW KEY. DELETE OLD KEY. MORE
    FUNCTIONALITY WILL BE ADDED BLAH BLAH BLAH
    --AGTB
    '''

    def get_client(self):

        client = boto3.client('iam',
                              region_name='us-east-1',
                              aws_access_key_id=self.AccessKey,
                              aws_secret_access_key=self.SecretAccessKey,
                              aws_session_token=self.SessionToken
                              )

        return client

    def get_all_iam_users(self):

        resp = self.get_client().list_users()
        all_users = resp['Users']
        all_users_lst = []

        for i in all_users:
            all_users_lst.append(i.get('UserName', []))

        return all_users_lst

    def get_user(self, user):

        paginator = self.get_client().get_paginator('list_access_keys')
        l_st = []
        for pag in paginator.paginate(UserName=user):
            l_st = pag['AccessKeyMetadata']

        return l_st[0].get('AccessKeyId')

    def get_last_access_key_used(self, user):
        access = self.get_user(user)

        client = self.get_client()

        response = client.get_access_key_last_used(
            AccessKeyId=access
        )
        return response['AccessKeyLastUsed']

    def update_access_key_status_inactive(self, user, key):
        client = self.get_client()

        client.update_access_key(
            AccessKeyId=key,
            Status='Inactive',
            UserName=user
        )

    def update_access_key_status_active(self, user, key):
        client = self.get_client()

        client.update_access_key(
            AccessKeyId=key,
            Status='Active',
            UserName=user
        )

    def create_access_key(self, user):
        client = self.get_client()
        client.create_access_key(
            UserName=user
        )

    def delete_access_key(self, user, key):
        client = self.get_client()
        client.delete_access_key(
            UserName=user,
            AccessKeyId=key,
        )

    def delete_user(self, user):
        self.get_client().delete_user(
            UserName=user
        )

    def create_user(self, user):
        self.get_client().create_user(
            UserName=user
        )

    def find_all_keys(self):

        all_keys = []
        all_users = self.get_all_iam_users()

        for name in all_users:

            all_keys.append(self.get_user(name))

        return all_keys

    def tag_users(self, user):
        client = self.get_client()

        client.tag_user(
            UserName=user,
            Tags=[
                {
                    'Key': 'CreatorName',
                    'Value': 'Person who created this'
                }
            ]
        )

    def un_tag_users(self, user):

        client = self.get_client()

        client.untag_user(
            UserName=user,
            TagKeys=[
                'CreatorName',
            ]
        )

    def list_tags(self, user):

        self.get_client().list_user_tags(
            UserName=user
        )

    def rotate_old_keys(self):

        today = datetime.datetime.now().replace(tzinfo=datetime.timezone.utc)
        get_all_users = self.get_all_iam_users()

        for name in get_all_users:
            response = self.get_client().list_access_keys(
                UserName=name,
            )
            for val in response.values():

                if isinstance(val, (list,)):
                    create_date = val[0]['CreateDate'].replace(tzinfo=datetime.timezone.utc)
                    duration = today - create_date

                    if duration.days <= 90:
                        print('We good')

                    elif duration.days > 90:
                        print('We not good')

                        self.update_access_key_status_inactive(val[0].get('UserName'), val[0].get('AccessKeyId'))
                        self.create_access_key(val[0].get('UserName'))
                        self.delete_access_key(val[0].get('UserName'), val[0].get('AccessKeyId'))

    def notify_user(self, user, contact):
        sender = "REQUIRED. Insert verified SES sender email address."
        recipient = contact
        configuration_set = "Insert config set if one is being used. If not comment this line out"
        subject = 'Your IAM User access key is tagged for rotation. Action Required'

        body_text = ("Your access key for" + user +
                     "has been marked for rotation. You have 7 days to utilize the new key"
                     "If no action is taken, your key will still be rotated."
                     )
        body_html = """<html>
        <head></head>
        <body>
            <h1> Your IAM User access key is tagged for rotation. ACTION REQUIRED</h1>
            <p> Action Required</p>
        </body>
        </html>
                    """
        charset = 'UTF-8'

        client = boto3.client('ses',
                              region_name='us-east-1',
                              aws_access_key_id=self.AccessKey,
                              aws_secret_access_key=self.SecretAccessKey,
                              aws_session_token=self.SessionToken
                              )
        try:

            response = client.send_email(
                Destination={
                    'ToAddresses': [
                        recipient,
                    ],
                },
                Message={
                    'Body': {
                        'Html': {
                            'Charset': charset,
                            'Data': body_html
                        },
                        'Text': {
                            'Charset': charset,
                            'Data': body_text,
                        },
                    },
                    'Subject': {
                        'Charset': charset,
                        'Data': subject,
                    },
                },
                Source=sender,

                ConfigurationSetName=configuration_set,

            )

        except ClientError as e:
            print(e.response['Error']['Message'])
        else:
            print("Email sent! Message ID:"),
            print(response['MessageId'])


if __name__ == '__main__':
    yo = Iam()
    yo.rotate_old_keys()