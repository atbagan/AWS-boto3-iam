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
    secrets = secret()
    sec_dict = json.loads(secrets.get_secret())

    ADName = sec_dict['username']
    ADPassword = sec_dict['password']

    os.environ["HTTP_PROXY"] = "http://" + ADName + ':' + ADPassword + "@cr-proxy.us.aegon.com:9090"
    os.environ["HTTPS_PROXY"] = "https://" + ADName + ':' + ADPassword + "@cr-proxy.us.aegon.com:9090"

    s = Session()

    AWSAccountNumber = '969859503720'
    AWSRole = 'UENTAWSCLOUDADMINS'
    url = "https://awsapi.us.aegon.com/default.aspx"
    payload = {"method": "usernameroleaccount", "username": ADName, "password": ADPassword,
               "account": AWSAccountNumber,
               "role": AWSRole}
    req = Request('POST', url, data=payload)
    prepped = req.prepare()

    resp = s.send(prepped,
                  stream=True,
                  verify=False
                  )
    creds = resp.content.decode().split(',')
    AccessKey = creds[2]
    SecretAccessKey = creds[0]
    SessionToken = creds[1]

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
                        if val[0].get('UserName') == 'agt_cassandra_snapshots':
                            print(val[0].get('UserName'), val[0].get('AccessKeyId'))
                            #self.update_access_key_status_inactive(val[0].get('UserName'), val[0].get('AccessKeyId'))
                            #self.create_access_key(val[0].get('UserName'))
                            #self.delete_access_key(val[0].get('UserName'), val[0].get('AccessKeyId'))
                        else:
                            break


if __name__ == '__main__':
    yo = Iam()
    yo.rotate_old_keys()
    #yo.list_tags('agt_cassandra_snapshots')
    #yo.tag_users('agt_cassandra_snapshots')
    #yo.un_tag_users('agt_cassandra_snapshots')
    # yo.iam_access_keys_need_changed()
    # yo.get_user('agt_cassandra_snapshots')
    # yo.get_last_access_key('agt_cassandra_snapshots')
    # yo.find_all_keys()
    # yo.get_all_old_keys()
