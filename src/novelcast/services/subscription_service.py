class SubscriptionService:
    def __init__(self, qm):
        self.qm = qm

    def add(self, url, title):
        self.qm.run("subscriptions.add", (url, title))

    def get(self, url):
        return self.qm.fetchone("subscriptions.get", (url,))