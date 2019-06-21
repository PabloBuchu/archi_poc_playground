import json

from locust import TaskSet, task, HttpLocust


class CodeBehaviour(TaskSet):
    @task(1)
    def code(self):
        self.client.post('/code', data=json.dumps({}))


class WebsiteCode(HttpLocust):
    task_set = CodeBehaviour
    min_wait = 1000
    max_wait = 2000
