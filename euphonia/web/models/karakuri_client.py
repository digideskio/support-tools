import requests
from bson import json_util


class Karakuri:

    def __init__(self, server):
        self.SERVER = server

    @staticmethod
    def execute_karakuri_call(url, method="GET", data=None):
        try:
            auth_header = {"Authorization": "auth_token=paulstoken"}
            if method == "GET":
                r = requests.get(url, headers=auth_header)
            elif method == "POST":
                r = requests.post(url, headers=auth_header, data=data)
            elif method == "DELETE":
                r = requests.delete(url, headers=auth_header)
            else:
                r = None
            if r is not None:
                response = json_util.loads(r.text)
                return response
            else:
                return None
        except RuntimeError:
            print "Failed to call: " + url

    # QUEUE FUNCTIONS
    def get_queues(self):
        get_url = "%s/queue" % self.SERVER
        response = self.execute_karakuri_call(get_url)
        return response

    def get_queue(self, queue_id):
        get_url = "%s/queue/%s" % (self.SERVER, queue_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def approve_queue(self, queue_id):
        get_url = "%s/queue/%s/approve" % (self.SERVER, queue_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def disapprove_queue(self, queue_id):
        get_url = "%s/queue/%s/disapprove" % (self.SERVER, queue_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def remove_queue(self, queue_id):
        get_url = "%s/queue/%s/remove" % (self.SERVER, queue_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def sleep_queue(self, queue_id, seconds=None):
        if seconds is None:
            get_url = "%s/queue/%s/sleep" % (self.SERVER, queue_id)
        else:
            get_url = "%s/queue/%s/sleep/%s" % (self.SERVER, queue_id, seconds)
        response = self.execute_karakuri_call(get_url)
        return response

    def wake_queue(self, queue_id):
        get_url = "%s/queue/%s/wake" % (self.SERVER, queue_id)
        response = self.execute_karakuri_call(get_url)
        return response

    # WORKFLO_w FUNC_tIONS
    def get_workflows(self):
        get_url = "%s/workflow" % self.SERVER
        response = self.execute_karakuri_call(get_url)
        return response

    def create_workflow(self, workflow=None):
        get_url = "%s/workflow" % self.SERVER
        response = self.execute_karakuri_call(get_url,
                                              method="POST",
                                              data=workflow)
        return response

    def get_workflow(self, workflow_id):
        get_url = "%s/workflow/%s" % (self.SERVER, workflow_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def update_workflow(self, workflow_name, workflow):
        get_url = "%s/workflow/%s" % (self.SERVER, workflow_name)
        response = self.execute_karakuri_call(get_url,
                                              method="POST",
                                              data=workflow)
        return response

    def delete_workflow(self, workflow_name):
        get_url = "%s/workflow/%s" % (self.SERVER, workflow_name)
        response = self.execute_karakuri_call(get_url,
                                              method="DELETE")
        return response

    def test_workflow(self, workflow):
        get_url = "%s/testworkflow" % self.SERVER
        response = self.execute_karakuri_call(get_url,
                                              method="POST",
                                              data=workflow)
        return response

    def process_workflow(self, workflow_id):
        get_url = "%s/workflow/%s/process" % (self.SERVER, workflow_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def approve_workflow(self, workflow_id):
        get_url = "%s/workflow/%s/approve" % (self.SERVER, workflow_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def disapprove_workflow(self, workflow_id):
        get_url = "%s/workflow/%s/disapprove" % (self.SERVER, workflow_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def remove_workflow(self, workflow_id):
        get_url = "%s/workflow/%s/remove" % (self.SERVER, workflow_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def sleep_workflow(self, workflow_id, seconds=None):
        if seconds is None:
            get_url = "%s/workflow/%s/sleep" % (self.SERVER, workflow_id)
        else:
            get_url = "%s/workflow/%s/sleep/%s" % (self.SERVER,
                                                   workflow_id,
                                                   seconds)
        response = self.execute_karakuri_call(get_url)
        return response

    def wake_workflow(self, workflow_id):
        get_url = "%s/workflow/%s/wake" % (self.SERVER, workflow_id)
        response = self.execute_karakuri_call(get_url)
        return response

    # TICKET FUNCTIONS
    def get_task(self, ticket_id):
        get_url = "%s/task/%s" % (self.SERVER, ticket_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def process_task(self, ticket_id):
        get_url = "%s/task/%s/process" % (self.SERVER, ticket_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def approve_task(self, ticket_id):
        get_url = "%s/task/%s/approve" % (self.SERVER, ticket_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def disapprove_task(self, ticket_id):
        get_url = "%s/task/%s/disapprove" % (self.SERVER, ticket_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def remove_task(self, ticket_id):
        get_url = "%s/task/%s/remove" % (self.SERVER, ticket_id)
        response = self.execute_karakuri_call(get_url)
        return response

    def sleep_task(self, ticket_id, seconds=None):
        if seconds is None:
            get_url = "%s/task/%s/sleep" % (self.SERVER, ticket_id)
        else:
            get_url = "%s/task/%s/sleep/%s" % (self.SERVER, ticket_id, seconds)
        response = self.execute_karakuri_call(get_url)
        return response

    def wake_task(self, ticket_id):
        get_url = "%s/task/%s/wake" % (self.SERVER, ticket_id)
        response = self.execute_karakuri_call(get_url)
        return response

    # ISSUE FUNCTIONS
    def get_issue(self, issue_id):
        get_url = "%s/issue/%s" % (self.SERVER, issue_id)
        response = self.execute_karakuri_call(get_url)
        return response
